"""
User Repository

Specialized repository for user management with authentication,
authorization, and user lifecycle operations.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, RepositoryError
from ..models.user import User, UserRole, UserStatus


class UserRepository(BaseRepository[User]):
    """
    User repository with authentication and authorization capabilities.
    
    Provides specialized operations for user management including
    authentication, role management, and security features.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            query = select(self.model).where(self.model.username == username)
            query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting user by username {username}: {e}")
            raise RepositoryError(f"Failed to get user by username: {e}")
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            query = select(self.model).where(self.model.email == email)
            query = query.where(self.model.is_deleted == False)
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting user by email {email}: {e}")
            raise RepositoryError(f"Failed to get user by email: {e}")
    
    async def get_by_role(self, role: UserRole,
                         skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by role."""
        try:
            query = select(self.model).where(self.model.role == role)
            query = query.where(self.model.is_deleted == False)
            query = query.order_by(self.model.username)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting users by role {role}: {e}")
            raise RepositoryError(f"Failed to get users by role: {e}")
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users."""
        try:
            query = select(self.model).where(
                and_(
                    self.model.status == UserStatus.ACTIVE,
                    self.model.is_deleted == False
                )
            )
            query = query.order_by(self.model.username)
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error(f"Error getting active users: {e}")
            raise RepositoryError(f"Failed to get active users: {e}")
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        try:
            user = await self.get_by_username(username)
            
            if user and user.check_password(password):
                # Record successful login
                user.record_login()
                await self.session.flush()
                return user
            
            # Record failed login attempt if user exists
            if user:
                user.record_failed_login()
                await self.session.flush()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error authenticating user {username}: {e}")
            raise RepositoryError(f"Failed to authenticate user: {e}")
    
    async def create_user(self, username: str, email: str, password: str,
                         first_name: Optional[str] = None,
                         last_name: Optional[str] = None,
                         role: UserRole = UserRole.VIEWER) -> User:
        """Create a new user with password."""
        try:
            # Check if username or email already exists
            existing_user = await self.get_by_username(username)
            if existing_user:
                raise RepositoryError(f"Username {username} already exists")
            
            existing_email = await self.get_by_email(email)
            if existing_email:
                raise RepositoryError(f"Email {email} already exists")
            
            # Create user
            user_data = {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': role
            }
            
            user = await self.create(user_data)
            user.set_password(password)
            
            await self.session.flush()
            return user
            
        except Exception as e:
            self.logger.error(f"Error creating user {username}: {e}")
            raise RepositoryError(f"Failed to create user: {e}")
    
    async def update_password(self, user_id: uuid.UUID, new_password: str) -> bool:
        """Update user password."""
        try:
            user = await self.get(user_id)
            if not user:
                return False
            
            user.set_password(new_password)
            user.password_changed_at = datetime.now(timezone.utc)
            
            await self.session.flush()
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating password for user {user_id}: {e}")
            return False
    
    async def lock_user(self, user_id: uuid.UUID, reason: Optional[str] = None) -> bool:
        """Lock a user account."""
        try:
            user = await self.get(user_id)
            if not user:
                return False
            
            user.status = UserStatus.LOCKED
            user.locked_until = datetime.now(timezone.utc) + timedelta(hours=24)  # Lock for 24 hours
            
            await self.session.flush()
            return True
            
        except Exception as e:
            self.logger.error(f"Error locking user {user_id}: {e}")
            return False
    
    async def unlock_user(self, user_id: uuid.UUID) -> bool:
        """Unlock a user account."""
        try:
            user = await self.get(user_id)
            if not user:
                return False
            
            user.unlock_account()
            await self.session.flush()
            return True
            
        except Exception as e:
            self.logger.error(f"Error unlocking user {user_id}: {e}")
            return False
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            # Total users
            total_query = select(func.count(self.model.id)).where(self.model.is_deleted == False)
            total_result = await self.session.execute(total_query)
            total_users = total_result.scalar()
            
            # Users by status
            status_query = (
                select(self.model.status, func.count(self.model.id))
                .where(self.model.is_deleted == False)
                .group_by(self.model.status)
            )
            status_result = await self.session.execute(status_query)
            status_counts = dict(status_result.all())
            
            # Users by role
            role_query = (
                select(self.model.role, func.count(self.model.id))
                .where(self.model.is_deleted == False)
                .group_by(self.model.role)
            )
            role_result = await self.session.execute(role_query)
            role_counts = dict(role_result.all())
            
            return {
                'total_users': total_users,
                'status_distribution': {
                    status.value: count for status, count in status_counts.items()
                },
                'role_distribution': {
                    role.value: count for role, count in role_counts.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user statistics: {e}")
            raise RepositoryError(f"Failed to get user statistics: {e}")
    
    async def search_users(self, search_term: str, skip: int = 0, 
                          limit: int = 100) -> List[User]:
        """Search users by username, email, or name."""
        search_fields = ['username', 'email', 'first_name', 'last_name']
        return await self.search(search_term, search_fields, skip, limit)
