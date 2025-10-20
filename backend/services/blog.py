from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.models import BlogPost
from backend.schemas.admin import BlogPostCreate, BlogPostUpdate

from .base import ServiceBase


class BlogService(ServiceBase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_posts(self) -> list[BlogPost]:
        result = await self.session.execute(
            select(BlogPost).order_by(BlogPost.created_at.desc())
        )
        posts = list(result.scalars().all())
        logger.debug("blog.list", count=len(posts))
        return posts

    async def create_post(self, payload: BlogPostCreate) -> BlogPost:
        post = BlogPost(**payload.model_dump())
        self.session.add(post)
        await self.session.commit()
        await self.session.refresh(post)
        logger.info("blog.created", post_id=post.id, slug=post.slug)
        return post

    async def update_post(self, post_id: int, payload: BlogPostUpdate) -> BlogPost:
        post = await self.session.get(BlogPost, post_id)
        if not post:
            raise LookupError("blog_not_found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(post, field, value)
        await self.session.commit()
        await self.session.refresh(post)
        logger.info("blog.updated", post_id=post.id)
        return post

    async def delete_post(self, post_id: int) -> None:
        post = await self.session.get(BlogPost, post_id)
        if not post:
            return
        await self.session.delete(post)
        await self.session.commit()
        logger.info("blog.deleted", post_id=post_id)
