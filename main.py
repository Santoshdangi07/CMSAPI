from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from datetime import datetime


app = Flask(__name__)
app.app_context().push()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blogs.db'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.String(255))
    content = db.Column(db.Text)
    creation_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('posts', lazy=True))
    is_private = db.Column(db.Boolean, default=False)


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post = db.relationship('Post', backref=db.backref('likes', lazy=True))
    user = db.relationship('User', backref=db.backref('likes', lazy=True))


db.create_all()


@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    if not name or not email or not password:
        abort(400, 'Missing required fields')
    user = User(name=name, email=email, password=password)
    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User created successfully'})
    except IntegrityError:
        db.session.rollback()
        abort(400, 'Email already exists')


@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get(user_id)
    if user:
        user_details = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            # Add other relevant fields
        }
        return jsonify(user_details)
    else:
        abort(404, 'User not found')


@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get(user_id)

    if user:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        if not name or not email or not password:
            abort(400, 'Missing required fields')

        user.name = name
        user.email = email
        user.password = password
        db.session.commit()
        return jsonify({'message': 'User updated successfully'})
    else:
        abort(404, 'User not found')


@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)

    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})
    else:
        abort(404, 'User not found')


@app.route('/posts', methods=['POST'])
def create_post():
    data = request.json
    title = data.get('title')
    description = data.get('description')
    content = data.get('content')
    is_private = data.get('is_private', False)
    user_id = data.get('user_id')

    if not title or not description or not content or not user_id:
        abort(400, 'Missing required fields')

    user = User.query.get(user_id)

    if not user:
        abort(404, 'User not found')

    post = Post(
        title=title,
        description=description,
        content=content,
        user=user,
        is_private=is_private
    )
    db.session.add(post)
    db.session.commit()
    return jsonify({'message': 'Post created successfully'})

@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.query.get(post_id)

    if post:
        if post.is_private:
            current_user_id = request.headers.get('User-Id')

            if current_user_id and str(post.user_id) == current_user_id:
                likes_count = len(post.likes)
                post_details = {
                    'id': post.id,
                    'title': post.title,
                    'description': post.description,
                    'content': post.content,
                    'creation_date': post.creation_date,
                    'likes_count': likes_count
                }
                return jsonify(post_details)
            else:
                abort(403, 'Access denied')
        else:
            likes_count = len(post.likes)
            post_details = {
                'id': post.id,
                'title': post.title,
                'description': post.description,
                'content': post.content,
                'creation_date': post.creation_date,
                'likes_count': likes_count
            }
            return jsonify(post_details)
    else:
        abort(404, 'Post not found')


@app.route('/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    post = Post.query.get(post_id)

    if post:
        data = request.json
        title = data.get('title')
        description = data.get('description')
        content = data.get('content')
        is_private = data.get('is_private')

        if not title or not description or not content:
            abort(400, 'Missing required fields')

        post.title = title
        post.description = description
        post.content = content
        post.is_private = is_private

        db.session.commit()
        return jsonify({'message': 'Post updated successfully'})
    else:
        abort(404, 'Post not found')


@app.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    post = Post.query.get(post_id)

    if post:
        # Check if the current user is the owner of the post
        current_user_id = request.headers.get('User-Id')  # Example: Extract user ID from request headers

        if current_user_id and str(post.user_id) == current_user_id:
            db.session.delete(post)
            db.session.commit()
            return jsonify({'message': 'Post deleted successfully'})
        else:
            abort(403, 'Access denied')  # Forbidden access error
    else:
        abort(404, 'Post not found')


@app.route('/posts', methods=['GET'])
def get_all_posts():
    posts = Post.query.all()
    results = []

    for post in posts:
        likes_count = len(post.likes)
        results.append({
            'id': post.id,
            'title': post.title,
            'description': post.description,
            'content': post.content,
            'creation_date': post.creation_date,
            'likes_count': likes_count
        })
    return jsonify(results)


@app.route('/likes', methods=['POST'])
def create_like():
    data = request.json
    post_id = data.get('post_id')
    user_id = data.get('user_id')

    if not post_id or not user_id:
        abort(400, 'Missing required fields')

    post = Post.query.get(post_id)
    user = User.query.get(user_id)

    if not post or not user:
        abort(404, 'Post or user not found')

    like = Like(post=post, user=user)

    db.session.add(like)
    db.session.commit()
    return jsonify({'message': 'Like created successfully'})


@app.route('/likes/<int:like_id>', methods=['GET'])
def get_like(like_id):
    like = Like.query.get(like_id)

    if like:
        like_details = {
            'id': like.id,
            'post_id': like.post_id,
            'user_id': like.user_id
            # Add other relevant fields
        }
        return jsonify(like_details)
    else:
        abort(404, 'Like not found')


@app.route('/likes/<int:like_id>', methods=['PUT'])
def update_like(like_id):
    like = Like.query.get(like_id)

    if like:
        current_user_id = request.headers.get('User-Id')

        if current_user_id and str(like.user_id) == current_user_id:
            data = request.json
            post_id = data.get('post_id')
            user_id = data.get('user_id')

            if not post_id or not user_id:
                abort(400, 'Missing required fields')

            post = Post.query.get(post_id)
            user = User.query.get(user_id)

            if not post or not user:
                abort(404, 'Post or user not found')

            like.post = post
            like.user = user

            db.session.commit()
            return jsonify({'message': 'Like updated successfully'})
        else:
            abort(403, 'Access denied')
    else:
        abort(404, 'Like not found')


@app.route('/likes/<int:like_id>', methods=['DELETE'])
def delete_like(like_id):
    like = Like.query.get(like_id)

    if like:
        # Check if the current user is the owner of the like
        current_user_id = request.headers.get('User-Id')

        if current_user_id and str(like.user_id) == current_user_id:
            db.session.delete(like)
            db.session.commit()
            return jsonify({'message': 'Like deleted successfully'})
        else:
            abort(403, 'Access denied')
    else:
        abort(404, 'Like not found')


if __name__ == '__main__':
    app.run(debug=True)
