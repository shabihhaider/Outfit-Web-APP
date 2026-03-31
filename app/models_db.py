"""
app/models_db.py
SQLAlchemy ORM models for the database layer.

Separate from engine/models.py (Pydantic) — these are the persistence models.
Conversion between the two is handled by app/utils.py:item_db_to_engine().
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.extensions import db


# ── Junction table: post ↔ vibe (many-to-many) ────────────────────────────────
post_vibes = db.Table(
    "post_vibes",
    db.Column("post_id", db.Integer, db.ForeignKey("shared_outfits.id", ondelete="CASCADE"), primary_key=True),
    db.Column("vibe_id", db.SmallInteger, db.ForeignKey("vibe_tags.id"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "users"

    id                     = db.Column(db.Integer, primary_key=True)
    email                  = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash          = db.Column(db.String(256), nullable=False)
    name                   = db.Column(db.String(80), nullable=False)
    gender                 = db.Column(db.String(10), nullable=False)   # men / women / unisex
    profile_photo_filename = db.Column(db.String(256), nullable=True)   # VTO person photo
    avatar_filename        = db.Column(db.String(256), nullable=True)   # Profile avatar image
    created_at             = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # ── Social profile fields ──────────────────────────────────────────────────
    username          = db.Column(db.String(30), unique=True, nullable=True, index=True)
    bio               = db.Column(db.String(150), nullable=True)
    follower_count    = db.Column(db.Integer, nullable=False, default=0)
    following_count   = db.Column(db.Integer, nullable=False, default=0)
    is_public         = db.Column(db.Boolean, nullable=False, default=True)
    vibe_preferences  = db.Column(db.Text, nullable=True)   # JSON array of vibe slugs
    fusion_mode_enabled = db.Column(db.Boolean, nullable=False, default=False)

    wardrobe_items = db.relationship(
        "WardrobeItemDB",
        backref="owner",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    outfit_history = db.relationship(
        "OutfitHistory",
        backref="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    saved_outfits = db.relationship(
        "SavedOutfit",
        backref="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    outfit_plans = db.relationship(
        "OutfitPlan",
        backref="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    shared_outfits_rel = db.relationship(
        "SharedOutfit",
        backref="author",
        cascade="all, delete-orphan",
        lazy="dynamic",
        foreign_keys="SharedOutfit.user_id",
    )

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "email":      self.email,
            "name":       self.name,
            "gender":     self.gender,
            "username":   self.username,
            "bio":        self.bio,
            "is_public":  self.is_public,
            "follower_count":  self.follower_count,
            "following_count": self.following_count,
            "fusion_mode_enabled": self.fusion_mode_enabled,
            "avatar_url": f"/uploads/{self.avatar_filename}" if self.avatar_filename else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def social_dict(self) -> dict:
        """Minimal public representation used in feed cards and follow lists."""
        return {
            "id":             self.id,
            "username":       self.username or f"user_{self.id}",
            "name":           self.name,
            "bio":            self.bio,
            "follower_count": self.follower_count,
            "following_count": self.following_count,
            "is_public":      self.is_public,
            "avatar_url":     f"/uploads/{self.avatar_filename}" if self.avatar_filename else None,
        }


class WardrobeItemDB(db.Model):
    __tablename__ = "wardrobe_items"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    image_filename = db.Column(db.String(256), nullable=False)
    category       = db.Column(db.String(20), nullable=False)   # top/bottom/outwear/shoes/dress/jumpsuit
    sub_category   = db.Column(db.String(40), nullable=True)    # CLIP-detected fine-grained label (e.g. "jeans", "blazer", "kurta")
    formality      = db.Column(db.String(10), nullable=False)   # casual/formal/both
    gender         = db.Column(db.String(10), nullable=False)   # men/women/unisex
    embedding      = db.Column(db.Text, nullable=False)         # JSON string of 1280 floats
    color_hue        = db.Column(db.Float, nullable=False)        # 0–360  → maps to dominant_hue in engine
    color_sat        = db.Column(db.Float, nullable=False)        # 0.0–1.0 → maps to dominant_sat in engine
    color_val        = db.Column(db.Float, nullable=False)        # 0.0–1.0 → maps to dominant_val in engine
    model_confidence = db.Column(db.Float, nullable=True)         # Model 1 top class probability (0.0–1.0)
    clip_confidence  = db.Column(db.Float, nullable=True)         # CLIP sub-category confidence (0.0–1.0)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self, image_url: str | None = None) -> dict:
        return {
            "id":               self.id,
            "category":         self.category,
            "sub_category":     self.sub_category,
            "formality":        self.formality,
            "gender":           self.gender,
            "image_url":        image_url or f"/uploads/{self.image_filename}",
            "model_confidence": self.model_confidence,
            "clip_confidence":  self.clip_confidence,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }


class OutfitHistory(db.Model):
    __tablename__ = "outfit_history"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    occasion         = db.Column(db.String(20), nullable=False)
    temperature_used = db.Column(db.Float, nullable=False)
    item_ids         = db.Column(db.Text, nullable=False)  # JSON array
    final_score      = db.Column(db.Float, nullable=False)
    confidence       = db.Column(db.String(10), nullable=False)
    template         = db.Column(db.String(5), nullable=False)
    logged_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    feedback = db.relationship(
        "OutfitFeedback",
        backref="history",
        cascade="all, delete-orphan",
        uselist=False,
    )


class SavedOutfit(db.Model):
    __tablename__ = "saved_outfits"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name        = db.Column(db.String(100), nullable=False)
    occasion    = db.Column(db.String(20), nullable=False)
    item_ids    = db.Column(db.Text, nullable=False)  # JSON array
    final_score = db.Column(db.Float, nullable=False)
    confidence  = db.Column(db.String(10), nullable=False)
    saved_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_saved_outfit_name_per_user"),
    )


class OutfitFeedback(db.Model):
    __tablename__ = "outfit_feedback"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    history_id = db.Column(db.Integer, db.ForeignKey("outfit_history.id", ondelete="CASCADE"), nullable=False, unique=True)
    rating     = db.Column(db.Integer, nullable=False)  # +1 or -1
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "history_id", name="uq_feedback_per_user_history"),
    )


class OutfitPlan(db.Model):
    __tablename__ = "outfit_plans"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date       = db.Column(db.Date, nullable=False)
    occasion        = db.Column(db.String(20), nullable=True)
    saved_outfit_id = db.Column(db.Integer, db.ForeignKey("saved_outfits.id", ondelete="SET NULL"), nullable=True)
    item_ids        = db.Column(db.Text, nullable=True)    # JSON array of wardrobe item IDs
    notes           = db.Column(db.String(200), nullable=True)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "plan_date", name="uq_user_plan_date"),
    )

    saved_outfit = db.relationship("SavedOutfit", backref=db.backref("plans", passive_deletes=True))

    def to_dict(self) -> dict:
        try:
            item_ids = json.loads(self.item_ids) if self.item_ids else []
        except (json.JSONDecodeError, TypeError):
            item_ids = []

        result = {
            "id":              self.id,
            "plan_date":       self.plan_date.isoformat(),
            "occasion":        self.occasion,
            "saved_outfit_id": self.saved_outfit_id,
            "item_ids":        item_ids,
            "notes":           self.notes,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
        }
        if self.saved_outfit:
            so = self.saved_outfit
            try:
                so_item_ids = json.loads(so.item_ids) if so.item_ids else []
            except (json.JSONDecodeError, TypeError):
                so_item_ids = []
            result["saved_outfit"] = {
                "id":          so.id,
                "name":        so.name,
                "occasion":    so.occasion,
                "item_ids":    so_item_ids,
                "final_score": so.final_score,
                "confidence":  so.confidence,
            }
        return result


class VibeTag(db.Model):
    """Reference table — 30 canonical vibe tags, seeded once, never changes."""
    __tablename__ = "vibe_tags"

    id     = db.Column(db.SmallInteger, primary_key=True)
    slug   = db.Column(db.String(50), unique=True, nullable=False)
    label  = db.Column(db.String(80), nullable=False)
    region = db.Column(db.Enum("global", "south-asian"), nullable=False, default="global")

    def to_dict(self) -> dict:
        return {"id": self.id, "slug": self.slug, "label": self.label, "region": self.region}


class SharedOutfit(db.Model):
    """A published post — links a SavedOutfit to the social feed."""
    __tablename__ = "shared_outfits"

    id                     = db.Column(db.Integer, primary_key=True)
    user_id                = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    saved_outfit_id        = db.Column(db.Integer, db.ForeignKey("saved_outfits.id", ondelete="CASCADE"), nullable=False)
    caption                = db.Column(db.String(300), nullable=True)
    preview_image_filename = db.Column(db.String(256), nullable=True)
    visibility             = db.Column(db.Enum("public", "followers", "private"), nullable=False, default="public")
    like_count             = db.Column(db.Integer, nullable=False, default=0)
    remix_count            = db.Column(db.Integer, nullable=False, default=0)
    view_count             = db.Column(db.Integer, nullable=False, default=0)
    remix_source_post_id   = db.Column(db.Integer, db.ForeignKey("shared_outfits.id", ondelete="SET NULL"), nullable=True)
    created_at             = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at             = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    vibes        = db.relationship("VibeTag", secondary="post_vibes", lazy="joined")
    saved_outfit = db.relationship("SavedOutfit", backref=db.backref("shared_posts", passive_deletes=True))

    __table_args__ = (
        db.Index("idx_so_feed",     "created_at", "id"),
        db.Index("idx_so_user",     "user_id", "created_at"),
        db.Index("idx_so_remix_src","remix_source_post_id"),
    )

    def to_dict(self, viewer_id: int | None = None, is_following: bool = False) -> dict:
        return {
            "id":          self.id,
            "user_id":     self.user_id,
            "user":        self.author.social_dict() if self.author else None,
            "caption":     self.caption,
            "preview_url": f"/uploads/{self.preview_image_filename}" if self.preview_image_filename else None,
            "visibility":  self.visibility,
            "like_count":  self.like_count,
            "remix_count": self.remix_count,
            "view_count":  self.view_count,
            "vibes":       [v.to_dict() for v in (self.vibes or [])],
            "remix_source_post_id": self.remix_source_post_id,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
            "is_liked":    False,   # overridden by route when viewer_id is known
        }


class Follow(db.Model):
    """Directed follow graph edge: follower → following."""
    __tablename__ = "follows"

    follower_id  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    following_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("idx_follows_follower",  "follower_id",  "created_at"),
        db.Index("idx_follows_following", "following_id", "created_at"),
        db.CheckConstraint("follower_id != following_id", name="chk_no_self_follow"),
    )


class OutfitLike(db.Model):
    """One row per (user, post) like. Toggle: insert on like, delete on unlike."""
    __tablename__ = "outfit_likes"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_outfit_id = db.Column(db.Integer, db.ForeignKey("shared_outfits.id", ondelete="CASCADE"), nullable=False)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "shared_outfit_id", name="uq_outfit_like"),
    )


class RemixLog(db.Model):
    """Append-only remix attribution log — feeds remix_count and chain endpoint."""
    __tablename__ = "remix_logs"

    id                      = db.Column(db.Integer, primary_key=True)
    source_shared_outfit_id = db.Column(db.Integer, db.ForeignKey("shared_outfits.id", ondelete="CASCADE"), nullable=False, index=True)
    remixer_user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at              = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class PostBookmark(db.Model):
    """Private post bookmarks — not visible to other users."""
    __tablename__ = "post_bookmarks"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_outfit_id = db.Column(db.Integer, db.ForeignKey("shared_outfits.id", ondelete="CASCADE"), nullable=False)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "shared_outfit_id", name="uq_post_bookmark"),
        db.Index("idx_bookmarks_user", "user_id", "created_at"),
    )


# ─────────────────────────────────────────────────────────────────────────────


class TryOnJob(db.Model):
    """
    Virtual Try-On job — one row per (user, item, person_photo) combination.

    Cache key: (user_id, item_id, person_photo_hash).
    When a matching row with status='ready' exists the result is served instantly
    without another API call.  The background worker updates status as it runs.

    Status lifecycle:  pending → processing → ready
                                           → failed
    """
    __tablename__ = "tryon_jobs"

    id                 = db.Column(db.Integer, primary_key=True)
    user_id            = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id            = db.Column(db.Integer, db.ForeignKey("wardrobe_items.id", ondelete="CASCADE"), nullable=False)
    person_photo_hash  = db.Column(db.String(64), nullable=False)   # SHA-256 hex of person photo bytes
    status             = db.Column(db.String(20), nullable=False, default="pending")
    result_filename    = db.Column(db.String(256), nullable=True)   # filename in uploads/ when ready
    error_msg          = db.Column(db.String(500), nullable=True)
    created_at         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at       = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        # One active job per (user, item, person_photo) combination
        db.Index("ix_tryon_cache_lookup", "user_id", "item_id", "person_photo_hash"),
    )

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "item_id":    self.item_id,
            "status":     self.status,
            "result_url": f"/uploads/{self.result_filename}" if self.result_filename else None,
            "error":      self.error_msg,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
