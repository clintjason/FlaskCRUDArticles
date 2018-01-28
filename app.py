from flask import Flask, render_template, url_for, flash, request, redirect, logging, session
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from wtforms.validators import InputRequired, Email, EqualTo, Length
from passlib.hash import sha256_crypt
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
#Mysql Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'XXXX'
app.config['MYSQL_PASSWORD'] = 'XXXX'
app.config['MYSQL_DB'] = 'XXXX'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # setting the cursor to return a dictionary rather than a tuple

#initial Mysql Config
mysql = MySQL(app)

#Articles = Articles()

@app.route('/')
def index():
	return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/articles')
def articles():
	cursor = mysql.connection.cursor()
	query_result = cursor.execute("SELECT * FROM articles")

	articles = cursor.fetchall()

	if query_result > 0:
		return render_template('articles.html',articles = articles)
	else:
		msg = "No articles found"
		return render_template('articles.html', msg=msg)
	cursor.close()

@app.route('/article/<string:id>')
def article(id):
	cursor = mysql.connection.cursor()
	result = cursor.execute("SELECT * FROM articles WHERE id = %s", [id])
	article = cursor.fetchone()
	if result > 0:
		return render_template('article.html',article=article)
	else:
		msg = "Missing Article"
		return render_template('notfound.html', msg=msg)

class RegisterForm(Form):
	name = StringField('Name',validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(), Email()])
	username = StringField('Username', validators=[InputRequired()])
	password = 	PasswordField('Password', validators=[InputRequired(),Length(min=4,max=12), EqualTo('confirm', message='passwords do not match')])
	confirm = PasswordField('Confirm Password', validators=[InputRequired(), Length(min=4,max=12)])

@app.route('/register',methods=['GET','POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		# Get the form values
		name = form.name.data
		username = form.username.data
		email = form.email.data
		password = form.password.data
		#encrypt the password
		encrypted_password = sha256_crypt.encrypt(str(password))
		# Now insert values in db
		#Firstly create a cursor object
		cursor = mysql.connection.cursor()

		#check if user exist
		q_result = cursor.execute("SELECT * FROM users WHERE username = %s", [username])
		if q_result > 0:
			#error = 'This Username is Unavailable'
			#return render_template('register.html',error= error)
			flash('Username Unavailable','danger')
			return redirect(url_for('register'))

		else:
			result = cursor.execute("INSERT INTO users (name, email, username, password) VALUES (%s,%s,%s,%s)", (name, email, username, encrypted_password))
			mysql.connection.commit() # saves changes
			cursor.close()	# close connection

			#use flash to define and render a response message
			flash('Registration Successful, Please Login', 'success')
			return redirect(url_for('login'))
	return render_template('register.html',form = form)

class LoginForm(Form):
	username = StringField('Username', validators=[InputRequired()])
	password = PasswordField('Password', validators= [InputRequired()])

@app.route('/login', methods=['GET','POST'])
def login():
	login_form = LoginForm(request.form)
	if request.method == 'POST' and login_form.validate():
		# Get form inputs
		#username = request.form['username']
		#candidate_password = request.form['password']
		username = login_form.username.data
		candidate_password = login_form.password.data
		#app.logger.info(username)
		#app.logger.info(candidate_password)

		cursor = mysql.connection.cursor()
		result = cursor.execute("SELECT * FROM users Where username = %s", [username])
		if result > 0:
			#get password from db
			data = cursor.fetchone()
			password = data['password']
			app.logger.info(password)

			#compare passwords
			if sha256_crypt.verify(candidate_password, password):
				# Login succeeds
				#Create session variables to start user session
				session['logged_in'] = True
				session['username'] = username
				flash('You are now Logged in','success')
				return redirect(url_for('dashboard'))
				#msg = 'Login Successfull'
				#return render_template('dashboard.html',msg = msg)
			else:
				flash('Invalid Password','danger')
				return redirect(url_for('login'))
			#close connection
			cursor.close()
		else:
			flash('Unknown Username','danger')
			return redirect(url_for('login'))

	return render_template('login.html', form=login_form)

#check if user is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please Login','danger')
			return redirect(url_for('login'))
	return wrap


@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are logged out', 'success')
	return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
	cursor = mysql.connection.cursor()
	query_result = cursor.execute("SELECT * FROM articles")

	articles = cursor.fetchall()

	if query_result > 0:
		return render_template('dashboard.html',articles = articles)
	else:
		msg = "No articles found"
		return render_template('dashboard.html', msg=msg)
	cursor.close()

class ArticleForm(Form):
	title = StringField('Title',validators=[InputRequired()])
	body = TextAreaField('Body', validators=[InputRequired()])

@app.route('/add_article', methods=['GET','POST'])
@is_logged_in
def add_article():
	article_form = ArticleForm(request.form)
	if request.method == 'POST' and article_form.validate():
		title = article_form.title.data
		body = article_form.body.data

		cursor = mysql.connection.cursor()
		query_result = cursor.execute('INSERT INTO articles(title, author, body) VALUES (%s, %s, %s)', [title, session['username'], body])

		mysql.connection.commit()
		cursor.close()

		flash('Article Created', 'success')
		return redirect(url_for('dashboard'))
	return render_template('add_article.html',form=article_form)

@app.route('/edit_article/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit_article(id):
	cursor = mysql.connection.cursor()
	result = cursor.execute("SELECT * FROM articles WHERE id = %s", [id])
	if result > 0:
		article = cursor.fetchone()
		
		#Populate form with data
		form = ArticleForm(request.form)

		form.title.data = article['title']
		form.body.data = article['body']
		cursor.close()
		if request.method == 'POST' and form.validate():
			#Get the actual form inputs
			#title = form.title.data
			#body = form.body.data
			# get the posted input values
			title = request.form['title']
			body = request.form['body']

			cur = mysql.connection.cursor()
			result = cur.execute("UPDATE articles SET title = %s, body = %s WHERE id = %s ", [title, body, id])

			mysql.connection.commit()
			cur.close()

			flash('Article Updated', 'success')
			return redirect(url_for('dashboard'))

		else:
			return render_template('edit_article.html', form=form)

	else:
		msg = "Unable to Edit Article"
        return render_template('dashboard.html', msg = msg)

@app.route('/delete_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    result = cur.execute("DELETE FROM articles WHERE id = %s ", [id])

    mysql.connection.commit()

    cur.close()

    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
	app.run(debug=True)
