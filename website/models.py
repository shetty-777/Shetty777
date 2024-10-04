from sqlalchemy import ForeignKey, Table, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from flask_login import UserMixin
from . import db

user_post_association = Table(
    'user_post_association',
    db.Model.metadata,
    db.Column('allusers_id', db.Integer, db.ForeignKey('allusers.id', ondelete="CASCADE"), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id', ondelete="CASCADE"), primary_key=True)
)

class AllUsers(db.Model, UserMixin):
	__tablename__ = 'allusers'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(75), unique=True, nullable=False)
	userrole = db.Column(db.String(15), nullable=False, default="subscriber")
	marked_posts = relationship('Post', secondary=user_post_association)
	comments = db.relationship('Comment', backref='allusers', passive_deletes=True)
	verified = db.Column(db.Boolean, nullable=False, default=False)
	date_subscribed = db.Column(db.DateTime(timezone=True), default=func.now())

	__mapper_args__ = {'polymorphic_identity':'allusers', 'polymorphic_on':"userrole",}

class User(AllUsers):
	__tablename__ = 'user'
	id = db.Column(db.Integer, ForeignKey('allusers.id'), primary_key=True)
	password1 = db.Column(db.String(200), nullable=False)
	password2 = db.Column(db.String(200), nullable=False)
    
	__mapper_args__ = {'polymorphic_identity':'user',}

class Subscriber(AllUsers):
	__tablename__ = 'subscriber'
	id = db.Column(db.Integer, ForeignKey('allusers.id'), primary_key=True)
	emailid = db.Column(db.String(75), unique=True, nullable=False)
	password = db.Column(db.String(200), nullable=False)	
    
	__mapper_args__ = {'polymorphic_identity':'subscriber',}

#----------------------------------------------------oo0oo---------------------------------------------------------#

class Post(db.Model):
	__tablename__ = 'post'
	id = db.Column(db.Integer, primary_key=True)
	url = db.Column(db.String(100), nullable=False, unique=True)
	category = db.Column(db.String(20), nullable=False)
	htmlfile = db.Column(db.String(50), nullable=False, unique=True)
	date_created = db.Column(db.DateTime(timezone=True), default=func.now())
	comments = db.relationship('Comment', backref='post', passive_deletes=True)

#----------------------------------------------------oo0oo---------------------------------------------------------#

class Comment(db.Model):
	__tablename__ = 'comment'
	id = db.Column(db.Integer, primary_key=True)
	rating = db.Column(db.Integer, nullable=True)
	text_content = db.Column(db.String(400), nullable=True)
	commentor = db.Column(db.Integer, db.ForeignKey('allusers.id', ondelete = "CASCADE"), nullable=False)
	post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete = "CASCADE"), nullable=False)
	date_created = db.Column(db.DateTime(timezone=True), default=func.now())

	__table_args__ = (
        CheckConstraint('rating >= 0 AND rating <= 10', name='check_rating_range'),
    )

if __name__ == '__main__':
    db.create_all()
