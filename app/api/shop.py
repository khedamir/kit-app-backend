from datetime import datetime
from uuid import uuid4
import os

from flask import Blueprint, request, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models.user import User
from ..models.student import StudentProfile
from ..models.shop import ShopItem, ShopPurchaseRequest


shop_bp = Blueprint("shop", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

SHOP_PHOTO_PATH_PREFIX = "/api/v1/uploads/"


def _coerce_persisted_photos(photos: list) -> list[str]:
    out: list[str] = []
    for p in photos:
        if not isinstance(p, str):
            continue
        s = p.strip()
        if s.startswith(SHOP_PHOTO_PATH_PREFIX) and ".." not in s:
            out.append(s)
    return out


def _serialize_item(item: ShopItem) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price_som": item.price_som,
        "quantity": item.quantity,
        "photos": list(item.photos or []),
        "sizes": item.sizes or [],
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _serialize_request(pr: ShopPurchaseRequest) -> dict:
    student = pr.student
    item = pr.item
    return {
        "id": pr.id,
        "status": pr.status,
        "quantity": pr.quantity,
        "selected_size": pr.selected_size,
        "total_price_som": pr.total_price_som,
        "admin_comment": pr.admin_comment,
        "approved_pickup_at": pr.approved_pickup_at.isoformat() if pr.approved_pickup_at else None,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "student": {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "group_name": student.group_name,
            "email": student.user.email if student and student.user else None,
        } if student else None,
        "item": _serialize_item(item) if item else None,
    }


def _get_current_user():
    user_id = int(get_jwt_identity())
    return db.session.get(User, user_id)


def _is_allowed_image(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


def _save_uploaded_photos(files) -> list[str]:
    saved_urls: list[str] = []
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        return saved_urls

    for image_file in files:
        if not image_file or not image_file.filename:
            continue
        original_name = secure_filename(image_file.filename)
        if not original_name or not _is_allowed_image(original_name):
            continue
        ext = original_name.rsplit(".", 1)[1].lower()
        new_name = f"{uuid4().hex}.{ext}"
        full_path = os.path.join(upload_folder, new_name)
        image_file.save(full_path)
        saved_urls.append(f"{SHOP_PHOTO_PATH_PREFIX}{new_name}")

    return saved_urls


def _remove_disk_files_for_item(item: ShopItem) -> None:
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        return
    upload_folder = os.path.abspath(upload_folder)
    for url in item.photos or []:
        if not isinstance(url, str) or not url.startswith(SHOP_PHOTO_PATH_PREFIX):
            continue
        safe_name = os.path.basename(url.replace("\\", "/"))
        if not safe_name or safe_name != url.replace("\\", "/").strip("/"):
            continue
        full_path = os.path.join(upload_folder, safe_name)
        if os.path.isfile(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass


def _require_admin():
    user = _get_current_user()
    if not user:
        return None, ({"message": "user not found"}, 404)
    if user.role != "admin":
        return None, ({"message": "only admin can access this endpoint"}, 403)
    return user, None


def _require_student():
    user = _get_current_user()
    if not user:
        return None, None, ({"message": "user not found"}, 404)
    if user.role != "student":
        return None, None, ({"message": "only student can access this endpoint"}, 403)
    profile = user.student_profile
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return user, profile, None


@shop_bp.get("/shop/items")
@jwt_required()
def get_shop_items():
    items = db.session.execute(
        db.select(ShopItem)
        .where(ShopItem.is_active == True, ShopItem.quantity > 0)
        .order_by(ShopItem.created_at.desc())
    ).scalars().all()
    return {"items": [_serialize_item(item) for item in items]}, 200


@shop_bp.get("/shop/items/<int:item_id>")
@jwt_required()
def get_shop_item(item_id: int):
    item = db.session.get(ShopItem, item_id)
    if not item or not item.is_active:
        return {"message": "item not found"}, 404
    return _serialize_item(item), 200


@shop_bp.post("/shop/purchase-requests")
@jwt_required()
def create_purchase_request():
    _, profile, error = _require_student()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    item_id = data.get("item_id")
    quantity = data.get("quantity", 1)
    selected_size = (data.get("selected_size") or "").strip() or None

    if not isinstance(item_id, int):
        return {"message": "item_id must be int"}, 400

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return {"message": "quantity must be int"}, 400
    if quantity < 1:
        return {"message": "quantity must be greater than 0"}, 400

    item = db.session.get(ShopItem, item_id)
    if not item or not item.is_active:
        return {"message": "item not found"}, 404
    if item.quantity < quantity:
        return {"message": "not enough quantity available"}, 400

    sizes = item.sizes or []
    if sizes and selected_size and selected_size not in sizes:
        return {"message": "selected size is not available"}, 400
    if sizes and not selected_size:
        return {"message": "selected_size is required for this item"}, 400

    total_price = item.price_som * quantity

    pr = ShopPurchaseRequest(
        student_id=profile.id,
        item_id=item.id,
        quantity=quantity,
        selected_size=selected_size,
        total_price_som=total_price,
        status="pending",
    )
    db.session.add(pr)
    db.session.commit()

    return _serialize_request(pr), 201


@shop_bp.get("/shop/purchase-requests/me")
@jwt_required()
def get_my_purchase_requests():
    _, profile, error = _require_student()
    if error:
        return error

    requests = db.session.execute(
        db.select(ShopPurchaseRequest)
        .where(ShopPurchaseRequest.student_id == profile.id)
        .order_by(ShopPurchaseRequest.created_at.desc())
    ).scalars().all()
    return {"requests": [_serialize_request(pr) for pr in requests]}, 200


@shop_bp.get("/admins/shop/items")
@jwt_required()
def admin_get_items():
    _, error = _require_admin()
    if error:
        return error

    items = db.session.execute(
        db.select(ShopItem).order_by(ShopItem.created_at.desc())
    ).scalars().all()
    if not items:
        return {"items": []}, 200
    ids = [i.id for i in items]
    count_rows = db.session.execute(
        db.select(ShopPurchaseRequest.item_id, func.count(ShopPurchaseRequest.id))
        .where(ShopPurchaseRequest.item_id.in_(ids))
        .group_by(ShopPurchaseRequest.item_id)
    ).all()
    count_map = {row[0]: row[1] for row in count_rows}
    out = []
    for item in items:
        row = dict(_serialize_item(item))
        row["purchase_requests_count"] = int(count_map.get(item.id, 0))
        out.append(row)
    return {"items": out}, 200


@shop_bp.post("/admins/shop/items")
@jwt_required()
def admin_create_item():
    _, error = _require_admin()
    if error:
        return error

    is_multipart = request.content_type and "multipart/form-data" in request.content_type
    if is_multipart:
        data = request.form or {}
        uploaded_photo_urls = _save_uploaded_photos(request.files.getlist("photos"))
        photos_raw = data.get("photo_urls", "")
        photos = [p.strip() for p in photos_raw.split(",") if p.strip()]
        photos.extend(uploaded_photo_urls)
        sizes_raw = data.get("sizes", "")
        sizes = [s.strip() for s in sizes_raw.split(",") if s.strip()]
    else:
        data = request.get_json(silent=True) or {}
        photos = data.get("photos") or []
        sizes = data.get("sizes") or []

    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip() or None

    if not name:
        return {"message": "name is required"}, 400
    if not isinstance(photos, list):
        return {"message": "photos must be an array"}, 400
    if not isinstance(sizes, list):
        return {"message": "sizes must be an array"}, 400

    try:
        price_som = int(data.get("price_som"))
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        return {"message": "price_som and quantity must be integers"}, 400

    if price_som < 0 or quantity < 0:
        return {"message": "price_som and quantity must be >= 0"}, 400

    item = ShopItem(
        name=name,
        description=description,
        price_som=price_som,
        quantity=quantity,
        photos=_coerce_persisted_photos(photos),
        sizes=[str(s).strip() for s in sizes if str(s).strip()],
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(item)
    db.session.commit()
    return _serialize_item(item), 201


@shop_bp.get("/uploads/<path:filename>")
def get_uploaded_photo(filename: str):
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        return {"message": "upload folder is not configured"}, 500
    return send_from_directory(upload_folder, filename)


@shop_bp.patch("/admins/shop/items/<int:item_id>")
@jwt_required()
def admin_patch_item(item_id: int):
    _, error = _require_admin()
    if error:
        return error

    item = db.session.get(ShopItem, item_id)
    if not item:
        return {"message": "item not found"}, 404

    is_multipart = request.content_type and "multipart/form-data" in request.content_type
    if is_multipart:
        data = request.form or {}
        uploaded_photo_urls = _save_uploaded_photos(request.files.getlist("photos"))
        photos_raw = data.get("photo_urls", "")
        photos = [p.strip() for p in photos_raw.split(",") if p.strip()]
        photos.extend(uploaded_photo_urls)
        sizes_raw = data.get("sizes", "")
        sizes = [s.strip() for s in sizes_raw.split(",") if s.strip()]
        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip() or None
        if not name:
            return {"message": "name is required"}, 400
        try:
            price_som = int(data.get("price_som"))
            quantity = int(data.get("quantity"))
        except (TypeError, ValueError):
            return {"message": "price_som and quantity must be integers"}, 400
        if price_som < 0 or quantity < 0:
            return {"message": "price_som and quantity must be >= 0"}, 400
        item.name = name
        item.description = description
        item.price_som = price_som
        item.quantity = quantity
        item.photos = _coerce_persisted_photos(photos)
        item.sizes = [str(s).strip() for s in sizes if str(s).strip()]
        if "is_active" in data:
            raw = data.get("is_active")
            if isinstance(raw, str):
                item.is_active = raw.lower() in ("1", "true", "yes", "on")
            else:
                item.is_active = bool(raw)
        db.session.commit()
        return _serialize_item(item), 200

    data = request.get_json(silent=True) or {}
    if "name" in data:
        item.name = (data.get("name") or "").strip()
    if "description" in data:
        item.description = (data.get("description") or "").strip() or None
    if "price_som" in data:
        try:
            value = int(data.get("price_som"))
        except (TypeError, ValueError):
            return {"message": "price_som must be int"}, 400
        if value < 0:
            return {"message": "price_som must be >= 0"}, 400
        item.price_som = value
    if "quantity" in data:
        try:
            value = int(data.get("quantity"))
        except (TypeError, ValueError):
            return {"message": "quantity must be int"}, 400
        if value < 0:
            return {"message": "quantity must be >= 0"}, 400
        item.quantity = value
    if "photos" in data:
        if not isinstance(data["photos"], list):
            return {"message": "photos must be an array"}, 400
        item.photos = _coerce_persisted_photos(data["photos"])
    if "sizes" in data:
        if not isinstance(data["sizes"], list):
            return {"message": "sizes must be an array"}, 400
        item.sizes = [str(s).strip() for s in data["sizes"] if str(s).strip()]
    if "is_active" in data:
        item.is_active = bool(data.get("is_active"))

    if not item.name:
        return {"message": "name is required"}, 400

    db.session.commit()
    return _serialize_item(item), 200


@shop_bp.delete("/admins/shop/items/<int:item_id>")
@jwt_required()
def admin_delete_item(item_id: int):
    _, error = _require_admin()
    if error:
        return error

    item = db.session.get(ShopItem, item_id)
    if not item:
        return {"message": "item not found"}, 404

    item.is_active = False
    db.session.commit()
    return "", 204


@shop_bp.delete("/admins/shop/items/<int:item_id>/permanent")
@jwt_required()
def admin_permanent_delete_item(item_id: int):
    _, error = _require_admin()
    if error:
        return error

    item = db.session.get(ShopItem, item_id)
    if not item:
        return {"message": "item not found"}, 404

    has_requests = db.session.execute(
        db.select(ShopPurchaseRequest.id).where(ShopPurchaseRequest.item_id == item_id).limit(1)
    ).first()
    if has_requests is not None:
        return {"message": "cannot delete: item has purchase requests"}, 409

    _remove_disk_files_for_item(item)
    db.session.delete(item)
    db.session.commit()
    return "", 204


@shop_bp.get("/admins/shop/purchase-requests")
@jwt_required()
def admin_get_purchase_requests():
    _, error = _require_admin()
    if error:
        return error

    status = (request.args.get("status") or "").strip()
    query = db.select(ShopPurchaseRequest).order_by(ShopPurchaseRequest.created_at.desc())
    if status:
        query = query.where(ShopPurchaseRequest.status == status)
    requests = db.session.execute(query).scalars().all()
    return {"requests": [_serialize_request(pr) for pr in requests]}, 200


@shop_bp.patch("/admins/shop/purchase-requests/<int:request_id>/approve")
@jwt_required()
def admin_approve_purchase_request(request_id: int):
    admin_user, error = _require_admin()
    if error:
        return error

    pr = db.session.get(ShopPurchaseRequest, request_id)
    if not pr:
        return {"message": "purchase request not found"}, 404
    if pr.status != "pending":
        return {"message": "purchase request is already processed"}, 400

    item = pr.item
    student = pr.student
    if not item or not student:
        return {"message": "purchase request references missing entities"}, 400

    if item.quantity < pr.quantity:
        return {"message": "not enough quantity in stock"}, 400
    if (student.total_som or 0) < pr.total_price_som:
        return {"message": "student does not have enough SOM"}, 400

    data = request.get_json(silent=True) or {}
    pickup_at_raw = (data.get("pickup_at") or "").strip()
    comment = (data.get("admin_comment") or "").strip() or None
    if not pickup_at_raw:
        return {"message": "pickup_at is required"}, 400

    try:
        pickup_at = datetime.fromisoformat(pickup_at_raw)
    except ValueError:
        return {"message": "pickup_at must be ISO datetime"}, 400

    item.quantity = item.quantity - pr.quantity
    student.total_som = (student.total_som or 0) - pr.total_price_som
    pr.status = "approved"
    pr.admin_comment = comment
    pr.approved_pickup_at = pickup_at
    pr.approved_by_admin_id = admin_user.id

    db.session.commit()
    return _serialize_request(pr), 200


@shop_bp.patch("/admins/shop/purchase-requests/<int:request_id>/reject")
@jwt_required()
def admin_reject_purchase_request(request_id: int):
    _, error = _require_admin()
    if error:
        return error

    pr = db.session.get(ShopPurchaseRequest, request_id)
    if not pr:
        return {"message": "purchase request not found"}, 404
    if pr.status != "pending":
        return {"message": "purchase request is already processed"}, 400

    data = request.get_json(silent=True) or {}
    pr.status = "rejected"
    pr.admin_comment = (data.get("admin_comment") or "").strip() or None
    db.session.commit()
    return _serialize_request(pr), 200


@shop_bp.patch("/admins/shop/purchase-requests/<int:request_id>/complete")
@jwt_required()
def admin_complete_purchase_request(request_id: int):
    _, error = _require_admin()
    if error:
        return error

    pr = db.session.get(ShopPurchaseRequest, request_id)
    if not pr:
        return {"message": "purchase request not found"}, 404
    if pr.status != "approved":
        return {"message": "only approved requests can be completed"}, 400

    data = request.get_json(silent=True) or {}
    pr.status = "completed"
    pr.admin_comment = (data.get("admin_comment") or "").strip() or pr.admin_comment
    db.session.commit()
    return _serialize_request(pr), 200
