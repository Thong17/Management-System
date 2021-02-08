from app import bcrypt, db, login_manager, upload, delete_photo, utc2local
from app import tblUser, tblBrand, tblCategory, tblProperty, tblProduct, tblColor, tblPhoto, tblValue, tblStock, tblProfile, tblDrawer, tblTransaction, tblQuantity, tblMoney, tblCustomer, tblPayment, tblAdvertise, tblOutcome, tblActivity, tblRole
from app import LoginForm, RegisterForm, CategoryForm, BrandForm, ProfileForm, RoleForm
from app import CategorySchema, ProductSchema, ColorSchema, BrandSchema, StockSchema, MoneySchema, DrawerSchema, TransactionSchema, PaymentSchema, ActivitySchema, RoleSchema, UserSchema
from flask import render_template, redirect, request, jsonify, Blueprint, url_for
from flask_login import login_user, logout_user, login_required, current_user
from uuid import uuid4
import json, simplejson, operator
from datetime import datetime, timedelta, date
from sqlalchemy import func
from decimal import Decimal
from functools import wraps

route = Blueprint('route', __name__)

def parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer

@parametrized
def is_authorized(f, r):
    def wrap(*args, **kwargs):
        roles = []
        # permissions = json.loads(current_user.roles[0].description)
        if current_user.is_authenticated:
            for role in current_user.roles:
                roles.append(role.role)
            if r in roles:
                return f(*args, **kwargs)
            else:
                return redirect(url_for('route.login'))
        else:
            return redirect(url_for('route.login'))
    return wrap

@login_manager.user_loader
def load_user(id):
    return tblUser.query.get(id)

@route.route('/')
def index():
    return render_template('views/index.html')


@route.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        msg = {
            'username': [],
            'password': [],
            'redirect': ''
        }
        if form.validate_on_submit():
            username = request.form['username']
            password = request.form['password']
            try:
                user = tblUser.query.filter_by(username=username).first()
                if user.isConfirm:
                    while user is not None:
                        isMatch = bcrypt.check_password_hash(
                            user.password, password)
                        if isMatch is True:
                            Activity = tblActivity(id=str(uuid4()), activity=user.username+' has logged in', type='Login', createdBy=user.id)
                            db.session.add(Activity)
                            db.session.commit()
                            login_user(user)
                            msg['redirect'] = '/'
                            return jsonify(msg)
                        msg['password'].append('Password does not match')
                        return jsonify(msg)
                    msg['username'].append('Username does not exist')
                else:
                    msg['username'].append('User may have been disabled! Contact your admin for more details')
                return jsonify(msg)
            except:
                msg['username'].append('Connection is not available')
                return jsonify(msg)
        for fieldName, errorMessages in form.errors.items():
            for err in errorMessages:
                msg[fieldName].append(err)
        return jsonify(msg)
    return render_template('views/login.html', form=form)


@route.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            username = request.form['username']
            gender = request.form['gender']
            birthdate = form.birthdate.data
            email = request.form['email']
            password = request.form['password']

            #Generate unique Id
            id = str(uuid4())
            profile_id = str(uuid4())

            #Encrypt the password field
            hashed_password = bcrypt.generate_password_hash(
                password).decode('utf-8')

            #User to register
            requestedUser = tblUser(id=id, firstname=firstname, lastname=lastname, username=username, gender=gender,
                                    birthdate=birthdate, email=email, password=hashed_password, publicId=str(uuid4()))

            try:
                db.session.add(requestedUser)
                db.session.commit()
                pid = str(uuid4())
                profileUser = tblProfile(id=pid, createdBy=id)
                db.session.add(profileUser)
                db.session.commit()
                login_user(requestedUser)
                return redirect('/')
            except SQLAlchemyError as error:
                print(str(error))
                db.session.rollback()
                return 'Register failed'
    return render_template('views/register.html', form=form)

@route.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect('/login')

@route.route('/user/save/<id>', methods=['POST'])
def save_user(id):
    user = tblUser.query.get(id)
    username = request.form['username']
    fullname = request.form['fullname']
    gender = request.form['gender']
    birthdate = request.form['birthdate']
    email = request.form['email']

    firstname = fullname.split(' ')[0]
    lastname = fullname.split(' ')[1]

    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified info from '+user.username+'/'+user.firstname+'/'+user.lastname+'/'+user.gender+'/'+str(user.birthdate)+'/'+user.email, type='Modify', createdBy=current_user.id)
    db.session.add(Activity)

    if birthdate == '':
        birthdate = None

    user.username = username
    user.firstname = firstname
    user.lastname = lastname
    user.gender = gender
    user.birthdate = birthdate
    user.email = email

    db.session.commit()

    return jsonify({'result': 'Success'})

@route.route('/profile')
@is_authorized('Administrator')
@login_required
def profile():
    form = ProfileForm()
    try:
        profile = tblProfile.query.get(current_user.profile[0].id)
    except:
        pid = str(uuid4())
        profile = tblProfile(id=pid, createdBy=current_user.id)
        db.session.add(profile)
        db.session.commit()
    return render_template('views/profile.html', form=form, profile=profile)

@route.route('/profile/save/<id>', methods=['POST'])
def save_profile(id):
    form = ProfileForm()
    profile = tblProfile.query.get(id)
    if form.validate_on_submit():
        status = request.form['status']
        phone = request.form['phone']
        company = request.form['company']
        hometown = request.form['hometown']
        location = request.form['location']
        bio = request.form['bio']

        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified profile from '+profile.status+'/'+profile.phone+'/'+profile.company+'/'+profile.hometown+'/'+profile.location+'/'+profile.bio, type='Modify', createdBy=current_user.id)
        db.session.add(Activity)

        profile.status = status
        profile.phone = phone
        profile.company = company
        profile.hometown = hometown
        profile.location = location
        profile.bio = bio 

        try:
            db.session.commit()
            return redirect('/profile')
        except:
            return render_template('views/profile.html', form=form)

    return render_template('views/profile.html', form=form)

@route.route('/profile/photo/<id>', methods=['POST'])
def save_photo(id):
    Profile = tblProfile.query.get(id)
    if Profile.photo != 'default.png':
        delete_photo('uploads', Profile.photo)
    jsons = []
    for file in request.files:
        photo = request.files[file]
        extension = photo.filename.rsplit('.', 1)[1]
        filename = str(uuid4()) + '.' + extension
        photo.filename = filename
        uploaded = upload.save(photo)
        Profile.photo = filename
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has uploaded his profile picture ', type='Modify', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        json = {
            'photoId': Profile.id,
            'src': filename,
        }
        jsons.append(json)
    return jsonify(jsons)

    
@route.route('/setting')
@login_required
def setting():
    return render_template('views/setting.html')


@route.route('/custome', methods=['POST', 'GET'])
@login_required
def custome():
    if request.method == 'POST':
        categories = tblCategory.query.all()
        category_schema = CategorySchema()
        category = category_schema.dump(categories, many=True)

        brands = tblBrand.query.all()
        brand_schema = BrandSchema()
        brand = brand_schema.dump(brands, many=True)

        result = {}
        result['categories'] = category
        result['brands'] = brand

        return jsonify(result)
    return render_template('views/custome.html')


@route.route('/category', methods=['POST', 'GET'])
@login_required
def categories():
    form = CategoryForm()
    categories = tblCategory.query.all()
    total = len(categories)
    today = []

    for item in categories:
        if datetime.now().date() == item.createdOn.date():
            today.append(item)
    if request.method == 'POST':
        msg = {
            'category': [],
            'redirect': '',
            'name': '',
            'id': '',
            'total': 0,
            'today': 0
        }
        if form.validate_on_submit():
            category = request.form['category']
            description = request.form['description']
            id = str(uuid4())
            Modal = tblCategory(id=id, category=category,
                                description=description, createdBy=current_user.id)
            msg['name'] = category
            msg['id'] = id
            try:
                Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added category: '+category+' in category', type='Add', createdBy=current_user.id)
                db.session.add(Activity)
                db.session.add(Modal)
                db.session.commit()
                total += 1
                today = len(today) + 1
                msg['redirect'] = '/category'
                msg['total'] = total
                msg['today'] = today
                return jsonify(msg)
            except:
                return 'Failed'
        for fieldName, errorMessages in form.errors.items():
            for err in errorMessages:
                msg[fieldName].append(err)
        return jsonify(msg)
    return render_template('views/category.html', form=form, categories=categories, today=today, total=total)


@route.route('/category/<id>', methods=['POST'])
def category(id):
    if request.form['data']:
        id = request.form['data']
        category = tblCategory.query.get(id)
        json = CategorySchema()
        result = json.dump(category)
    return jsonify(result)


@route.route('/category/property', methods=['POST'])
@login_required
def add_property():
    categoryId = request.form['categoryId']
    _property = request.form['property']
    _type = request.form['type']
    description = request.form['description']
    id = str(uuid4())
    Category = tblCategory.query.get(categoryId)

    Modal = tblProperty(id=id, property=_property, type=_type,
                        description=description, categoryId=categoryId, createdBy=current_user.id)

    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added property: '+_property+' in category '+Category.category, type='Add', createdBy=current_user.id)
    db.session.add(Activity)
    db.session.add(Modal)
    db.session.commit()
    return jsonify({'id': id, 'property': _property, 'type': _type, 'description': description, 'msg': ''})

@route.route('/property/remove/<id>', methods=['POST'])
@login_required
def remove_property(id):
    if request.form['data']:
        id = request.form['data']
        try:
            _property = tblProperty.query.get(id)
            Category = tblCategory.query.get(categoryId)
            Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted property: '+_property.property+' in category '+Category.category, type='Delete', createdBy=current_user.id)
            db.session.add(Activity)
            db.session.delete(_property)
            db.session.commit()
            return jsonify({'msg': 'Property deleted'})
        except:
            return 'Failded'

@route.route('/property/update/<id>', methods=['POST'])
def update_property(id):
    _property = tblProperty.query.get(id)

    new_property = request.form['property']
    new_type = request.form['type']
    new_description = request.form['description']

    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified property from '+_property.property+'/'+_property.type+'/'+_property.description, type='Modify', createdBy=current_user.id)
    db.session.add(Activity)

    _property.property = new_property
    _property.type = new_type
    _property.description = new_description

    try:
        db.session.commit()
        return jsonify({'id': id, 'property': new_property, 'type': new_type, 'description': new_description})
    except:
        return jsonify({'msg': 'Failed'})

@route.route('/category/remove/<id>', methods=['POST'])
def remove_category(id):
    category = tblCategory.query.get(id)
    try: 
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted category: '+category.category, type='Delete', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.delete(category)
        db.session.commit()
        categories = tblCategory.query.all()
        today = []
        for item in categories:
            if datetime.now().date() == item.createdOn.date():
                today.append(item)
        return jsonify({'msg': 'Success', 'today': len(today), 'total': len(categories)})
    except:
        return jsonify({'msg': 'Failed'})

@route.route('/category/update/<id>', methods=['POST'])
def udpate_category(id):
    category = tblCategory.query.get(id)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified category from '+category.category, type='Modify', createdBy=current_user.id)
    db.session.add(Activity)
    try:
        category.category = request.form['data']
        db.session.commit()
        return jsonify({'category': request.form['data'], 'msg': 'Success'})
    except: 
        return jsonify({'msg': 'Failed'})

@route.route('/brand', methods=['POST', 'GET'])
@login_required
def brands():
    brands = tblBrand.query.all()
    categories = tblCategory.query.with_entities(tblCategory.id, tblCategory.category).all()
    form = BrandForm()
    if request.method == 'POST':
        msg = {
            'brand': [],
            'redirect': '',
            'name': '',
            'id': ''
        }
        if form.validate_on_submit():
            brand = request.form['brand']
            description = request.form['description']
            id = str(uuid4())
            Modal = tblBrand(id=id, brand=brand, description=description, createdBy=current_user.id)
            msg['name'] = brand
            msg['id'] = id
            try:
                db.session.add(Modal)
                Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added brand: '+brand+' in brand', type='Add', createdBy=current_user.id)
                db.session.add(Activity)
                db.session.commit()
                msg['redirect'] = '/brand'
                return jsonify(msg)
            except:
                return 'Failed'
        for fieldName, errorMessages in form.errors.items():
            for err in errorMessages:
                msg[fieldName].append(err)
        return jsonify(msg)
    return render_template('views/product.html', brands=brands, form=form, categories=categories)

@route.route('/brand/remove/<id>', methods=['POST'])
def remove_brand(id):
    brand = tblBrand.query.get(id)
    try: 
        db.session.delete(brand)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted brand: '+brand.brand, type='Delete', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        return jsonify({'msg': 'Success'})
    except:
        return jsonify({'msg': 'Failed'})

@route.route('/brand/update/<id>', methods=['POST'])
def udpate_brand(id):
    brand = tblBrand.query.get(id)
    try:
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified brand from '+brand.brand, type='Modify', createdBy=current_user.id)
        db.session.add(Activity)
        brand.brand = request.form['data']
        db.session.commit()
        return jsonify({'brand': request.form['data'], 'msg': 'Success'})
    except: 
        return jsonify({'msg': 'Failed'})

@route.route('/theme/change', methods=['POST'])
@login_required
def theme():
    theme = request.form['data']
    user = tblUser.query.get(current_user.id)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified theme from '+user.theme, type='Modify', createdBy=current_user.id)
    db.session.add(Activity)
    user.theme = theme
    db.session.commit()
    return jsonify({'theme': theme})

@route.route('/product/add', methods=['POST'])
def add_product():
    product = request.form['product']
    barcode = request.form['barcode']
    price = request.form['price']
    discount = request.form['discount']
    category = request.form['category']
    currency = request.form['currency']
    period = request.form['period']
    description = request.form['description']
    brand = request.form['brand']
    isStock = request.form['isStock']

    if isStock == 'true':
        isStock = True
    else:
        isStock = False
    
    if period == '':
        period = None

    id = str(uuid4())

    Model = tblProduct(id=id, product=product, barcode=barcode, isStock=isStock, price=price, discount=discount, period=period, currency=currency, description=description, createdBy=current_user.id, categoryId=category, brandId=brand)
    
    db.session.add(Model)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added product '+product, type='Add', createdBy=current_user.id)
    db.session.add(Activity)
    db.session.commit()

    return jsonify({'data': 'Success', 'id': id})


@route.route('/product', methods=['POST'])
@login_required
def products():
    id = request.form['data']
    Products = tblProduct.query.with_entities(tblProduct.id, tblProduct.product, tblProduct.createdOn, tblProduct.price, tblProduct.photo, tblProduct.categoryId, tblProduct.discount).filter_by(brandId=id).all()
    products = []
    for Product in Products:
        price = simplejson.dumps({"price": Product.price})
        price = json.loads(price)
        Category = tblCategory.query.get(Product.categoryId)
        arrival = datetime.now().date() - Product.createdOn.date()
        product = {
            'id': Product.id,
            'product': Product.product,
            'photo': Product.photo,
            'category': Category.category,
            'arrival': arrival.days,
            'discount': Product.discount
        }
        product.update(price)
        products.append(product)
    return jsonify(products)

@route.route('/product/photo/<id>', methods=['POST'])
def product_photo(id):
    alt = request.form['name']
    Product = tblProduct.query.get(id)
    if Product.photo != 'default.png':
        delete_photo('uploads', Product.photo)
    jsons = []
    for file in request.files:
        photo = request.files[file]
        extension = photo.filename.rsplit('.', 1)[1]
        filename = str(uuid4()) + '.' + extension
        photo.filename = filename
        uploaded = upload.save(photo)
        Product.photo = filename
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has upload photo for product: '+Product.product, type='Upload', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        json = {
            'photoId': Product.id,
            'src': filename,
            'alt': alt
        }
        jsons.append(json)
    return jsonify(jsons)

@route.route('/product/color/<id>', methods=['POST'])
def upload_color(id):
    hex = request.form['hex']
    color = request.form['color']
    cid = str(uuid4())
    Color = tblColor(id=cid, color=color, hex=hex, createdBy=current_user.id, productId=id)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added color '+color+' in product', type='Add', createdBy=current_user.id)
    db.session.add(Activity)
    db.session.add(Color)
    db.session.commit()

    return jsonify({'id': cid, 'hex': hex, 'color': color})

@route.route('/color/photo/<id>', methods=['POST'])
def color_photo(id):
    cid = request.form['color']
    alt = request.form['name']
    color = tblColor.query.get(cid)
    jsons = []
    for file in request.files:
        photo = request.files[file]
        extension = photo.filename.rsplit('.', 1)[1]
        filename = str(uuid4()) + '.' + extension
        photo.filename = filename
        uploaded = upload.save(photo)
        pid = str(uuid4())
        Photo = tblPhoto(id=pid, src=filename, alt=alt, createdBy=current_user.id, colorId=cid, productId=id)
        db.session.add(Photo)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has upload photo for color: '+color.color, type='Upload', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
    color = tblColor.query.get(cid)
    json = ColorSchema()
    result = json.dump(color)
    return jsonify(result)

@route.route('/product/<id>', methods=['POST', 'GET'])
@login_required
def product(id):
    product = tblProduct.query.get(id)
    if request.method == 'POST':
        json = ProductSchema()
        result = json.dump(product)
        category = tblCategory.query.get(product.categoryId)
        c = CategorySchema()
        result['category'] = c.dump(category)
        return jsonify(result)
    return render_template('views/product_details.html', product=product)

@route.route('/value/add', methods=['POST'])
def add_value():
    product_id = request.form['product']
    property_id = request.form['property']
    value = request.form['value']
    price = request.form['price']
    currency = request.form['currency']
    description = request.form['description']

    id = str(uuid4())
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added value '+value+' in product', type='Add', createdBy=current_user.id)
    db.session.add(Activity)
    model = tblValue(id=id, value=value, price=price, currency=currency, description=description, createdBy=current_user.id, productId=product_id, propertyId=property_id)
    db.session.add(model)
    
    db.session.commit()
    return jsonify({'id': id, 'value': value, 'price': price, 'currency': currency, 'description': description, 'property': property_id})

@route.route('/product/save/<id>', methods=['POST'])
def save_product(id):
    Product = tblProduct.query.get(id)

    category = request.form['category']
    product = request.form['product']
    barcode = request.form['barcode']
    currency = request.form['currency']
    price = request.form['price']
    isStock = request.form['isStock']
    period = request.form['period']
    discount = request.form['discount']
    description = request.form['description']

    Category = tblCategory.query.get(category)

    if isStock == 'true':
        isStock = True
    else:
        isStock = False

    if period == '':
        period = None

    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified product from '+Product.product+'/'+Product.barcode+'/'+str(Product.isStock)+'/'+Product.currency+'/'+str(Product.price)+'/'+Product.description+'/'+str(Product.discount)+'/'+str(Product.period)+'/'+Category.category, type='Modify', createdBy=current_user.id)
    db.session.add(Activity)

    Product.product = product
    Product.barcode = barcode
    Product.isStock = isStock
    Product.currency = currency
    Product.price = price
    Product.description = description
    Product.categoryId = category
    Product.discount = discount
    Product.period = period

    db.session.commit()
    return jsonify({'data': 'success'})

@route.route('/product/remove/<id>', methods=['POST'])
def remove_product(id):
    product = tblProduct.query.get(id)
    if product.colors:
        for color in product.colors:
            if color.photos:
                for photo in color.photos:
                    delete_photo('uploads', photo.src)
    if product.photo != 'default.png':
        delete_photo('uploads', product.photo)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'result': 'Success'})

@route.route('/value/save/<id>', methods=['POST'])
def save_value(id):
    value = tblValue.query.get(id)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified value from '+value.value+'/'+str(value.price)+'/'+value.currency+'/'+value.description+' in product: '+value.productId, type='Modify', createdBy=current_user.id)
    db.session.add(Activity)
    value.value = request.form['value']
    value.price = request.form['price']
    value.currency = request.form['currency']
    value.description = request.form['description']
    try:
        db.session.commit()
        return jsonify({'resutl': 'success', 'value': value.value, 'price': value.price, 'currency': value.currency, 'description': value.description})
    except:
        return jsonify({'resutl': 'failed'})

@route.route('/value/remove/<id>', methods=['POST'])
def remove_value(id):
    value = tblValue.query.get(id)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted value: '+value.value+' in product', type='Delete', createdBy=current_user.id)
    db.session.add(Activity)
    db.session.delete(value)
    db.session.commit()
    return jsonify({'result': 'Success'})

@route.route('/color/<id>', methods=['POST'])
def get_color(id):
    color = tblColor.query.get(id)
    json = ColorSchema()
    result = json.dump(color)
    return jsonify(result)

@route.route('/color/save/<id>', methods=['POST'])
def save_color(id):
    color = tblColor.query.get(id)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified color from '+color.color+'/'+color.hex+' in product', type='Modify', createdBy=current_user.id)
    db.session.add(Activity)
    color.color = request.form['color']
    color.hex = request.form['hex']
    db.session.commit()
    return jsonify({'color': color.color, 'hex': color.hex})

@route.route('/color/remove/<id>', methods=['POST'])
def remove_color(id):
    color = tblColor.query.get(id)
    if color.colorsOfProduct.stocks:
        for stock in color.colorsOfProduct.stocks:
            if stock.color == id:
                stock.color = ''
    if color.photos:
        for photo in color.photos:
            delete_photo('uploads', photo.src)
    try:
        db.session.delete(color)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted color: '+color.color+' in product', type='Delete', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        return jsonify({'result': 'Success', 'photos': []})
    except:
        return jsonify({'result': 'Failed'})

@route.route('/property/<id>', methods=['POST'])
def _property(id):
    category = tblCategory.query.get(id)
    c = CategorySchema()
    result_property = c.dump(category)
    
    product = tblProduct.query.get(request.form['product'])
    p = ProductSchema()
    if product:
        result_product = p.dump(product)
    else:
        result_product = ''
    
    return jsonify({'property': result_property, 'product': result_product})

@route.route('/stock')
@login_required
def stocks():
    products = tblProduct.query.all()
    brands = tblBrand.query.all()
    categories = tblCategory.query.all()
    return render_template('views/stock.html', products=products, brands=brands, categories=categories)

@route.route('/stock/product/<id>')
@login_required
def stock(id):
    product = tblProduct.query.get(id)
    total_stock = 0
    sum_cost = 0
    total_cost = 0
    if product.stocks:
        for stock in product.stocks:
            total_stock += stock.quantity
            sum_cost = stock.cost * stock.quantity
            total_cost += sum_cost

    product.stocks.sort(key=lambda r: r.createdOn, reverse=True)
    stocks = []
    if product.colors:
        for color in product.colors:
            total_quantity = 0
            if product.stocks:
                for stock in product.stocks:
                    if stock.color == color.id:
                        total_quantity += stock.quantity
            
            stock = {
                'color': color.color,
                'quantity': total_quantity
            }

            stocks.append(stock)

    return render_template('views/product_stock.html', product=product, total_stock=total_stock, total_cost=total_cost, stocks=stocks)

@route.route('/stock/add', methods=['POST'])
def add_stock():
    color = request.form['color']
    cost = request.form['cost']
    quantity = request.form['quantity']
    currency = request.form['currency']
    rate = request.form['rate']
    adjust = request.form['adjust']
    product = request.form['product']

    if adjust == '':
        adjust = 0.00

    if rate == '':
        rate = 4000

    id = str(uuid4())

    model = tblStock(id=id, cost=cost, quantity=quantity, currency=currency, rate=rate, adjust=adjust, productId=product, color=color, createdBy=current_user.id)
    amount = (float(cost) * int(quantity)) - float(adjust)
    outcome = tblOutcome(id=id, amount=amount, createdBy=current_user.id)
    try:
        db.session.add(model)
        db.session.add(outcome)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added stock: '+id+' in product', type='Add', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        total_stock = 0
        total_costs = 0
        total_cost = 0
        for stock in model.stocksOfProduct.stocks:
            total_stock += stock.quantity
            total_cost = stock.cost * stock.quantity
            total_costs += total_cost 
        return jsonify({'data': 'success', 'id': id, 'cost': cost, 'quantity': quantity, 'currency': currency, 'rate': rate, 'adjust': adjust, 'color': color, 'total_stock': total_stock, 'createdOn': model.createdOn.strftime('%Y-%m-%d %H:%M:%S'), 'total_cost': total_costs})
    except:
        return jsonify({'data': 'failed'})


@route.route('/stock/delete/<id>', methods=['POST'])
def delete_stock(id):
    stock = tblStock.query.get(id)
    outcome = tblOutcome.query.get(id)
    total_stock = 0
    total_costs = 0
    total_cost = 0

    delete_stock = stock.quantity
    delete_cost = stock.cost * stock.quantity
    for s in stock.stocksOfProduct.stocks:
        total_stock += s.quantity
        total_cost = s.cost * s.quantity
        total_costs += total_cost
    try:
        db.session.delete(outcome)
        db.session.delete(stock)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted stock: '+stock.id+' in product', type='Delete', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        total_stock -= delete_stock
        total_costs -= delete_cost
        return jsonify({'data': 'success', 'total_stock': total_stock, 'total_cost': total_costs})
    except:
        return jsonify({'data': 'failed'}) 
    
@route.route('/stock/save/<id>', methods=['POST'])
def save_stock(id):
    stock = tblStock.query.get(id)
    outcome = tblOutcome.query.get(id)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified stock from '+stock.color+'/'+str(stock.cost)+'/'+stock.currency+'/'+str(stock.rate)+'/'+str(stock.quantity)+'/'+str(stock.adjust)+' in product', type='Modify', createdBy=current_user.id)
    db.session.add(Activity)

    stock.color = request.form['color']
    stock.cost = request.form['cost']
    stock.currency = request.form['currency']
    stock.rate = request.form['rate']
    stock.quantity = request.form['quantity']
    stock.adjust = request.form['adjust']
    outcome.amount = (float(stock.cost) * int(stock.quantity)) - float(stock.adjust)
    try:
        db.session.commit()
        total_stock = 0
        total_costs = 0
        total_cost = 0
        if stock.stocksOfProduct.stocks:
            for s in stock.stocksOfProduct.stocks:
                total_stock += s.quantity
                total_cost = s.cost * s.quantity
                total_costs += total_cost

        stocks = []
        if stock.stocksOfProduct.colors:
            for color in stock.stocksOfProduct.colors:
                total_quantity = 0
                if stock.stocksOfProduct.stocks:
                    for s in stock.stocksOfProduct.stocks:
                        if s.color == color.id:
                            total_quantity += s.quantity
                st = {
                    'color': color.color,
                    'quantity': total_quantity
                }
                stocks.append(st)

        return jsonify({'data': 'success', 'total_stock': total_stock, 'stocks': stocks, 'total_cost': total_costs})
    except:
        return jsonify({'data': 'failed'})

@route.route('/financial', defaults={'arg': None})
@route.route('/financial/<arg>')
@login_required
def financial(arg):
    if arg is not None:
        return render_template('views/financial.html', authentication='require')
    else:
        return render_template('views/financial.html', authentication='')


@route.route('/authenticate', methods=['POST'])
@login_required
def authenticate():
    msg = {
        'password': [],
        'redirect': ''
    }
    password = request.form['password']
    try:
        if password == '':
            msg['password'].append('Password cannot be empty')
            return jsonify(msg)
        else:
            isMatch = bcrypt.check_password_hash(current_user.password, password)
            if isMatch is True:
                token = str(uuid4())
                current_user.token = token
                msg['redirect'] = '/cashing/'+token
                db.session.commit()
                return jsonify(msg)
            msg['password'].append('Password is not correct')
            return jsonify(msg)
    except:
        msg['password'].append('Connection is not available')
        return jsonify(msg)

@route.route('/cashing/<token>')
@login_required
def cashing(token):
    if token == current_user.token:   
        products = tblProduct.query.all()
        brands = tblBrand.query.all()
        categories = tblCategory.query.all()
        return render_template('views/cashing.html', products=products, brands=brands, categories=categories)
    else:
        return redirect('/financial/authentication')

@route.route('/order/product/<id>', methods=['POST'])
def order(id):
    product = tblProduct.query.get(id)
    data = json.loads(request.form['data'])
    description = product.product
    oid = request.form['id']

    resultObj = {
        'data': {},
        'result': ''
    }

    if data['colorId'] == '':
        data['colorId'] = None

    if data['discount'] == '':
        data['discount'] = 0

    discount = Decimal(data['discount'])
    price = Decimal(data['price'])
    quantity = Decimal(data['quantity'])

    # Check

    amount = price * (1 - discount / 100)
    pprice = price * (1 - discount / 100)

    for v in data['values']:
        value = tblValue.query.get(v['valueId'])
        pprice -= value.price
        description += '-'+value.value

    tid = str(uuid4())
    transaction = tblTransaction(id=tid, discount=discount, price=pprice, amount=amount, description=description, createdBy=current_user.id)
    db.session.add(transaction)

    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added transaction: '+description, type='Add', createdBy=current_user.id)
    db.session.add(Activity)

    if product.isStock:
        if len(product.stocks) > 0:
            total_stocks = 0
            sum_stocks = 0
            for stock in product.stocks:
                if stock.color == data['colorId']:
                    sum_stocks += stock.quantity
                elif stock.color == '':
                    sum_stocks += stock.quantity
                total_stocks += stock.quantity
            available = sum_stocks - quantity
            if available >= 0:
                sum_quantity = quantity
                for stock in product.stocks:
                    if sum_quantity > 0 and stock.quantity > 0:
                        qid = str(uuid4())
                        if stock.color == data['colorId'] or stock.color == '':
                            if stock.quantity < sum_quantity:
                                stock_quantity = stock.quantity
                                stock.quantity = 0
                                Quantity = tblQuantity(id=qid, stock=stock_quantity, quantity=sum_quantity, stockId=stock.id, transactionId=tid)
                                db.session.add(Quantity)
                                transaction.quantity += stock_quantity
                                sum_quantity -= stock_quantity
                            else:
                                Quantity = tblQuantity(id=qid, stock=sum_quantity, quantity=sum_quantity, stockId=stock.id, transactionId=tid)
                                db.session.add(Quantity)
                                transaction.quantity += sum_quantity
                                stock.quantity -= sum_quantity
                                sum_quantity = 0
                amount *= quantity
                total_stocks -= quantity
                db.session.commit()
                resultObj['result'] = 'success'
                resultObj['data'] = {'id': tid, 'amount': amount, 'stock': total_stocks, 'quantity': quantity, 'price': price, 'isStock': True, 'discount': discount}
            else:
                resultObj['result'] = 'failed'
                resultObj['data'] = {'message': 'This color has only '+str(sum_stocks)+' left'}
        else:
            resultObj['result'] = 'failed'
            resultObj['data'] = {'message': 'This color is not available'} 
    else:
        transaction.quantity = quantity
        db.session.commit()
        amount *= quantity
        resultObj['result'] = 'success'
        resultObj['data'] = {'id': tid, 'amount': amount, 'quantity': quantity, 'price': price, 'isStock': False, 'discount': discount}
    return jsonify(resultObj)

@route.route('/drawer/create', methods=['POST'])
def create_drawer():
    data = json.loads(request.form['data'])
    id = str(uuid4())
    Drawer = tblDrawer(id=id, key=current_user.token, rate=data['rate'], counter=data['counter'], createdBy=current_user.id)
    db.session.add(Drawer)
    total = 0
    
    for money in data['moneys']:
        if money['currency'] == 'KHR':
            value = float(money['money']) / float(data['rate'])
        else:
            value = money['money']
        mid = str(uuid4())
        Money = tblMoney(id=mid, money=money['money'], currency=money['currency'], unit=money['unit'], drawerId=id, value=value)
        total += float(money['total'])
        db.session.add(Money)
    Drawer.startCost = total
    current_user.drawer = id

    #continue
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has opened drawer', type='Open', createdBy=current_user.id)
    db.session.add(Activity)

    db.session.commit()
    startedOn = Drawer.startedOn.strftime("%b %d %Y %H:%M:%S")
    return jsonify({'data': 'Success', 'startedOn': startedOn, 'id':id})

@route.route('/drawer/end/<id>', methods=['POST'])
def end_drawer(id):
    Drawer = tblDrawer.query.get(id)
    Drawer.endedOn = datetime.utcnow()
    current_user.drawer = ''
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has closed drawer', type='Close', createdBy=current_user.id)
    db.session.add(Activity)
    db.session.commit()
    return jsonify({'data': 'Success'})

@route.route('/drawer/<id>', methods=['POST'])
def get_drawer(id):
    try:
        Drawer = tblDrawer.query.get(id)
        if Drawer is None:
            moneys = []
            rate = 4000
            counter = 'Default'
            return jsonify({'data': moneys, 'rate': rate, 'counter': counter})
        else:
            jsonObj = DrawerSchema()
            drawer = jsonObj.dump(Drawer)
            return jsonify({'data': drawer['moneys'], 'rate': drawer['rate'], 'counter': drawer['counter']})
    except:
        return jsonify({'data': []})

@route.route('/payment', methods=['POST'])
def payment():
    Payments = tblPayment.query.with_entities(tblPayment.id).all()
    Drawer = tblDrawer.query.get(current_user.drawer)
    transactions = json.loads(request.form['data'])
    if transactions:
        id = str(uuid4())
        invoice = 'INV'+ str(len(Payments) + 1).zfill(7)
        Payment = tblPayment(id=id, invoice=invoice, createdBy=current_user.id, drawerId=current_user.drawer)
        db.session.add(Payment)
        total = 0
        for transaction in transactions:
            Transaction = tblTransaction.query.get(transaction)
            total += Transaction.amount * Transaction.quantity
            Payment.transactions.append(Transaction)
        Payment.amount = total
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has ordered invoice: '+invoice, type='Order', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        p = PaymentSchema()
        result = p.dump(Payment)
        
        return jsonify({'result': 'Success', 'data': result, 'rate': Drawer.rate})
    else:
        return jsonify({'result': 'No transaction added'})

@route.route('/payment/<id>', methods=['POST'])
def get_payment(id):
    Drawer = tblDrawer.query.get(current_user.drawer)
    Payment = tblPayment.query.get(id)
    transactions = json.loads(request.form['data'])

    if transactions:
        total = 0
        for transaction in transactions:
            Transaction = tblTransaction.query.get(transaction)
            if Transaction.quantities:
                quantity = 0
                for q in Transaction.quantities:
                    quantity += q.quantity
                Transaction.quantity = quantity
            total += Transaction.price * quantity
            if Transaction not in Payment.transactions:
                Payment.transactions.append(Transaction)
        Payment.amount = total
        db.session.commit()

    p = PaymentSchema()
    payment = p.dump(Payment)
    return jsonify({'data': payment, 'rate': Drawer.rate})

@route.route('/transaction/delete/<id>', methods=['POST'])
def delete_transaction(id):
    Transaction = tblTransaction.query.get(id)
    pid = request.form['data']
    quantity = 0
    if Transaction.quantities:
        for q in Transaction.quantities:
            quantity += Transaction.quantity
        q.soq.quantity += quantity
    if pid != '':
        Payment = tblPayment.query.get(pid)
        Payment.amount -= Transaction.price
    # try:
    db.session.delete(Transaction)
    db.session.commit()
    return jsonify({'result': 'Success', 'quantity': quantity})
    # except:
    #     return jsonify({'result': 'Transaction could not found'})


@route.route('/checkout/<id>', methods=['POST'])
def checkout(id):
    payment = tblPayment.query.get(id)
    drawer = tblDrawer.query.get(current_user.drawer)
    jsonObj = json.loads(request.form['data'])
    amounts = jsonObj['amounts']
    amount = 0
    for a in amounts:
        if a['currency'] != 'USD':
            a['amount'] = Decimal(a['amount']) / drawer.rate
        amount += Decimal(a['amount'])
    
    if amount >= payment.amount:
        moneys = []
        change = Decimal(amount) - payment.amount
        moneyObj = {
            'money': change,
            'currency': 'USD'
        }
        for money in (sorted(drawer.moneys, key=operator.attrgetter('value'), reverse=True)):
            convertMoney = 0
            if money.currency != 'USD':
                convertMoney = money.money / drawer.rate
            else:
                convertMoney = money.money
            if money.unit > 0 and convertMoney <= change:
                for unit in range(int(money.unit)):
                    if convertMoney <= change:
                        moneys.append({
                            'money': round(money.money, 4),
                            'currency': money.currency
                        })
                        money.unit -= 1
                        change -= convertMoney
                        moneyObj['money'] = round(change, 4)
        moneys.append(moneyObj)
        for transaction in payment.transactions:
            transaction.isComplete = True
            transaction.profit = transaction.price * transaction.quantity
            if transaction.quantities:
                for quantity in transaction.quantities:
                    transaction.profit -= quantity.soq.cost * quantity.quantity

        payment.isComplete = True
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has checked out payment '+payment.invoice, type='Payment', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        return jsonify({'result': 'Success', 'change': moneys, 'rate': drawer.rate})
    else:
        return jsonify({'result': 'Not enough money'})

@route.route('/transaction')
def transaction():
    Transactions = tblTransaction.query.order_by(tblTransaction.createdOn).all()
    Payments = tblPayment.query.order_by(tblPayment.invoice).all()
    return render_template('views/transaction.html', transactions=Transactions, payments=Payments)

@route.route('/transaction/reverse', methods=['POST'])
def undo_transaction():
    id = request.form['id']
    transaction = tblTransaction.query.get(id)
    if transaction.quantities:
        if transaction.transactions:
            transaction.transactions[0].isComplete = False
        for q in transaction.quantities:
            q.soq.quantity += q.stock
    try:
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted transaction '+transaction.description, type='Delete', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.delete(transaction)
        db.session.commit()   
        return jsonify({'data': 'Success'})
    except:
        return jsonify({'data': 'Could not find the selected transaction'})
    
@route.route('/invoice/search', methods=['POST'])
def search_invoice():
    input = request.form['data']
    return jsonify({'data': 'Success'})

@route.route('/report')
def report():
    return render_template('views/report.html')

@route.route('/income', methods=['POST'])
def income():
    Transactions = None
    f = request.form['filter']
    s = request.form['start']
    e = request.form['end']

    if s != '' and e != '':
        s = datetime.strptime(request.form['start'], '%Y-%m-%d')
        e = datetime.strptime(request.form['end'], '%Y-%m-%d')
        Transactions = tblTransaction.query.order_by(tblTransaction.createdOn).filter(tblTransaction.createdOn.between(s, e))
    else:
        Transactions = tblTransaction.query.order_by(tblTransaction.createdOn).all()


    data = []
    labels = []

    if Transactions:
        for transaction in Transactions:
            createdOn = None
            if f == 'daily':
                createdOn = utc2local(transaction.createdOn).strftime("%Y-%m-%d")
            elif f == 'monthly':
                createdOn = utc2local(transaction.createdOn).strftime("%Y-%m")
            elif f =='yearly':
                createdOn = utc2local(transaction.createdOn).strftime("%Y")
            obj = {
                'label': createdOn,
                'data': 0
            }

            if createdOn in labels:
                for d in data:
                    if d['label'] == createdOn:
                        d['data'] += transaction.amount * transaction.quantity
            else:
                obj['data'] = transaction.amount * transaction.quantity
                data.append(obj)
                labels.append(createdOn)

    if s == '' and e == '':
        s = current_user.createdOn.strftime("%Y-%m-%d")
        e = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify({'data': data, 'oldest': s, 'latest': e})

@route.route('/outcome', methods=['POST'])
def outcome():
    Outcome = None
    f = request.form['filter']
    s = request.form['start']
    e = request.form['end']

    if s != '' and e != '':
        s = datetime.strptime(request.form['start'], '%Y-%m-%d') - timedelta(days=1)
        e = datetime.strptime(request.form['end'], '%Y-%m-%d') + timedelta(days=1)
        Outcome = tblOutcome.query.order_by(tblOutcome.createdOn).filter(tblOutcome.createdOn.between(s, e))
    else:
        Outcome = tblOutcome.query.order_by(tblOutcome.createdOn).all()


    data = []
    labels = []

    if Outcome:
        for outcome in Outcome:
            createdOn = None
            if f == 'daily':
                createdOn = utc2local(outcome.createdOn).strftime("%Y-%m-%d")
            elif f == 'monthly':
                createdOn = utc2local(outcome.createdOn).strftime("%Y-%m")
            elif f =='yearly':
                createdOn = utc2local(outcome.createdOn).strftime("%Y")
            obj = {
                'label': createdOn,
                'data': 0
            }

            if createdOn in labels:
                for d in data:
                    if d['label'] == createdOn:
                        d['data'] += outcome.amount
            else:
                obj['data'] = outcome.amount
                data.append(obj)
                labels.append(createdOn)

    if s == '' and e == '':
        s = current_user.createdOn.strftime("%Y-%m-%d")
        e = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify({'data': data, 'oldest': s, 'latest': e})

@route.route('/profit', methods=['POST'])
def profit():
    Transactions = None
    f = request.form['filter']
    s = request.form['start']
    e = request.form['end']

    if s != '' and e != '':
        s = datetime.strptime(request.form['start'], '%Y-%m-%d')
        e = datetime.strptime(request.form['end'], '%Y-%m-%d')
        Transactions = tblTransaction.query.order_by(tblTransaction.createdOn).filter(tblTransaction.createdOn.between(s, e))
    else:
        Transactions = tblTransaction.query.order_by(tblTransaction.createdOn).all()


    data = []
    labels = []

    if Transactions:
        for transaction in Transactions:
            createdOn = None
            if f == 'daily':
                createdOn = utc2local(transaction.createdOn).strftime("%Y-%m-%d")
            elif f == 'monthly':
                createdOn = utc2local(transaction.createdOn).strftime("%Y-%m")
            elif f =='yearly':
                createdOn = utc2local(transaction.createdOn).strftime("%Y")
            obj = {
                'label': createdOn,
                'data': 0
            }

            if createdOn in labels:
                for d in data:
                    if d['label'] == createdOn:
                        d['data'] += transaction.profit
            else:
                obj['data'] = transaction.profit
                data.append(obj)
                labels.append(createdOn)

    if s == '' and e == '':
        s = current_user.createdOn.strftime("%Y-%m-%d")
        e = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify({'data': data, 'oldest': s, 'latest': e})

@route.route('/sale', methods=['POST'])
def sale():
    Transactions = None
    f = request.form['filter']
    s = request.form['start']
    e = request.form['end']

    if s != '' and e != '':
        s = datetime.strptime(request.form['start'], '%Y-%m-%d')
        e = datetime.strptime(request.form['end'], '%Y-%m-%d')
        Transactions = tblTransaction.query.filter(tblTransaction.createdOn.between(s, e))
    else:
        Transactions = tblTransaction.query.all()


    data = []
    labels = []
    dates = []

    if Transactions:
        for transaction in Transactions:
            dates.append(datetime.strftime(transaction.createdOn, '%Y-%m-%d'))
            obj = {
                'label': transaction.sale.username,
                'data': 0
            }

            if transaction.sale.username in labels:
                for d in data:
                    if transaction.sale.username == d['label']:
                        d['data'] += transaction.profit
            else:
                obj['data'] = transaction.profit
                data.append(obj)
                labels.append(transaction.sale.username)

    if s == '' and e == '':
        s = current_user.createdOn.strftime("%Y-%m-%d")
        e = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify({'data': data, 'oldest': s, 'latest': e})



@route.route('/product_report', methods=['POST'])
def product_report():
    Transactions = None
    f = request.form['filter']
    s = request.form['start']
    e = request.form['end']

    if s != '' and e != '':
        s = datetime.strptime(request.form['start'], '%Y-%m-%d')
        e = datetime.strptime(request.form['end'], '%Y-%m-%d')
        Transactions = tblTransaction.query.filter(tblTransaction.createdOn.between(s, e))
    else:
        Transactions = tblTransaction.query.all()

    data = []
    labels = []
    dates = []

    if Transactions:
        for transaction in Transactions:
            dates.append(datetime.strftime(transaction.createdOn, '%Y-%m-%d'))
            obj = {
                'label': transaction.description,
                'data': 0
            }

            if transaction.description in labels:
                for d in data:
                    if transaction.description == d['label']:
                        d['data'] += transaction.profit
            else:
                obj['data'] = transaction.profit
                data.append(obj)
                labels.append(transaction.description)

    if s == '' and e == '':
        s = current_user.createdOn.strftime("%Y-%m-%d")
        e = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify({'data': data, 'oldest': s, 'latest': e})

@route.route('/quantity_report', methods=['POST'])
def quantity_report():
    Transactions = None
    f = request.form['filter']
    s = request.form['start']
    e = request.form['end']

    if s != '' and e != '':
        s = datetime.strptime(request.form['start'], '%Y-%m-%d')
        e = datetime.strptime(request.form['end'], '%Y-%m-%d')
        Transactions = tblTransaction.query.filter(tblTransaction.createdOn.between(s, e))
    else:
        Transactions = tblTransaction.query.all()

    data = []
    labels = []
    dates = []

    if Transactions:
        for transaction in Transactions:
            dates.append(datetime.strftime(transaction.createdOn, '%Y-%m-%d'))
            obj = {
                'label': transaction.description,
                'data': 0
            }

            if transaction.description in labels:
                for d in data:
                    if transaction.description == d['label']:
                        d['data'] += transaction.quantity
            else:
                obj['data'] = transaction.quantity
                data.append(obj)
                labels.append(transaction.description)

    if s == '' and e == '':
        s = current_user.createdOn.strftime("%Y-%m-%d")
        e = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    return jsonify({'data': data, 'oldest': s, 'latest': e})


@route.route('/financial_report')
@login_required
def financial_report():
    return render_template('views/financial_report.html')

@route.route('/account')
@login_required
def account():
    users = tblUser.query.all()
    return render_template('views/account_report.html', users=users)

@route.route('/account/report', methods=['POST'])
@login_required
def account_report():
    activities = tblActivity.query.order_by(tblActivity.createdOn.desc()).all()
    result = []

    for a in activities:
        obj = {
            'activity': a.activity,
            'createdBy': a.createdBy,
            'createdOn': utc2local(a.createdOn).strftime("%Y-%m-%d"),
            'type': a.type,
            'id': a.id
        }
        result.append(obj)

    return jsonify(result)

@route.route('/sale_report')
def sale_report():
    return render_template('views/sale_report.html')

@route.route('/financial', methods=['POST'])
def get_financial():
    transactions = tblTransaction.query.all()
    payments = tblPayment.query.all()

    transactionObj = {
        'complete': [],
        'pending': []
    }

    paymentObj = {
        'complete': [],
        'pending': []
    }

    if payments:
        for payment in payments:
            if payment.isComplete == True:
                paymentObj['complete'].append(payment.id)
            else:
                paymentObj['pending'].append(payment.id)

    if transactions:
        for transaction in transactions:
            if transaction.isComplete == True:
                transactionObj['complete'].append(transaction.id)
            else:
                transactionObj['pending'].append(transaction.id)
    return jsonify({'transactionObj': transactionObj, 'paymentObj': paymentObj})

@route.route('/advertise')
@login_required
def advertise():
    Advertises = tblAdvertise.query.all()
    return render_template('views/advertise.html', advertises=Advertises)

@route.route('/advertise/photo/<id>', methods=['POST'])
def add_advertise(id):
    isMain = False
    if id == 'main':
        isMain = True
    jsons = []
    for file in request.files:
        photo = request.files[file]
        extension = photo.filename.rsplit('.', 1)[1]
        filename = str(uuid4()) + '.' + extension
        photo.filename = filename
        uploaded = upload.save(photo)
        id = str(uuid4())

        Advertise = tblAdvertise(id=id, src=filename, alt="Advertise", main=isMain, createdBy=current_user.id)
        db.session.add(Advertise)
        
        json = {
            'photoId': id,
            'src': filename,
        }
        jsons.append(json)
    Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has uploaded advertise photo: '+Advertise.src, type='Upload', createdBy=current_user.id)
    db.session.add(Activity)
    db.session.commit()
    return jsonify(jsons)

@route.route('/advertise/delete/<id>', methods=['POST'])
def delete_advertise(id):
    Advertise = tblAdvertise.query.get(id)
    try:
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted advertise photo: '+Advertise.src, type='Delete', createdBy=current_user.id)
        db.session.add(Activity)
        delete_photo('uploads', Advertise.src)
        db.session.delete(Advertise)
        db.session.commit()
        return jsonify({'data': 'Success'})
    except:
        return jsonify({'data': 'Failed'})

@route.route('/home')
def home():
    categories = tblCategory.query.all()
    brands = tblBrand.query.all()
    products = tblProduct.query.all()
    advertises = tblAdvertise.query.all()
    return render_template('views/home.html', categories=categories, brands=brands, products=products, advertises=advertises)

@route.route('/about')
def about():
    return render_template('views/about.html')

@route.route('/contact')
def contact():
    return render_template('views/contact.html')

@route.route('/activity')
@login_required
def activity():
    Activities = tblActivity.query.order_by(tblActivity.createdOn.desc()).all()
    activities = []
    if Activities:
        for activity in Activities:
            actObj = {
                'activity': activity.activity,
                'type': activity.type,
                'createdOn': utc2local(activity.createdOn),
                'createdBy': '',
            }
            Users = tblUser.query.with_entities(tblUser.username, tblUser.id).all()
            for user in Users:
                if user.id == activity.createdBy:
                    actObj['createdBy'] = user.username
            activities.append(actObj)

    return render_template('views/activity.html', activities=activities)

@route.route('/password/change', methods=['POST'])
def change_password():
    curpwd = request.form['current']
    newpwd = request.form['newpwd']
    conpwd = request.form['conpwd']
    isMatch = bcrypt.check_password_hash(current_user.password, curpwd)
    data = ''
    if isMatch:
        if newpwd == conpwd:  
            hashed_password = bcrypt.generate_password_hash(newpwd).decode('utf-8')
            current_user.password = hashed_password
            db.session.commit()
            data = 'Success'
        else:
            data = 'Confirm password is not matched'
    else:
        data = 'Entered password is incorrect'

    return jsonify(data)

@route.route('/product/favorite/<id>', methods=['POST'])
def product_favorite(id):
    product = tblProduct.query.get(id)
    isSaved = False
    listJson = json.loads(product.listFavorite)
    listFavorite = []
    for obj in listJson:
        listFavorite.append(obj)
    
    if current_user.id in listFavorite:
        listFavorite.remove(current_user.id)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has removed '+product.product+' from favorite', type='Remove', createdBy=current_user.id)
        db.session.add(Activity)
    else:
        listFavorite.append(current_user.id)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added '+product.product+' to favorite', type='Add', createdBy=current_user.id)
        db.session.add(Activity)
        isSaved = True
    
    product.listFavorite = json.dumps(listFavorite)
    db.session.commit()
    return jsonify({'msg': 'Success', 'data': isSaved})

@route.route('/role')
@login_required
def role():
    form = RoleForm() 
    roles = tblRole.query.all()
    users = tblUser.query.all()
    return render_template('views/role.html', roles=roles, form=form, users=users)

@route.route('/role', methods=['POST'])
def get_roles():
    roles = tblRole.query.all()
    r = RoleSchema(many=True)
    Roles = r.dump(roles)
    return jsonify(Roles)

@route.route('/role/add', methods=['POST'])
def add_role():
    msg = {
            'role': [],
            'redirect': '',
            'name': '',
            'id': '',
        }
    role = request.form['role']
    description = request.form['description']
    id = str(uuid4())
    Modal = tblRole(id=id, role=role,
                        description=description, createdBy=current_user.id)
    msg['name'] = role
    msg['id'] = id
    try:
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has added role: '+role+' in category', type='Add', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.add(Modal)
        db.session.commit()
        msg['redirect'] = 'Success'
        return jsonify(msg)
    except:
        return 'Failed'
    for fieldName, errorMessages in form.errors.items():
        for err in errorMessages:
            msg[fieldName].append(err)
    return jsonify(msg)

@route.route('/role/change/<id>', methods=['POST'])
def change_role(id):
    role = tblRole.query.get(id)
    user = tblUser.query.get(request.form['data'])
    user.roles.clear()
    user.roles.append(role)
    try:
        db.session.commit()
        return jsonify({'data': 'Success', 'role': role.role})
    except:
        return jsonify({'data': 'Faild'})

@route.route('/role/update/<id>', methods=['POST'])
def update_role(id):
    Role = tblRole.query.get(id)
    old = Role.role
    data = request.form['data']
    Role.role = data
    try:
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified theme from '+old, type='Modify', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        return jsonify({'msg': 'Success'})
    except:
        return jsonify({'msg': 'Faild'})
    
@route.route('/role/remove/<id>', methods=['POST'])
@login_required
def remove_role(id):
    try:
        role = tblRole.query.get(id)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has deleted role: '+role.role+' in role', type='Delete', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.delete(role)
        db.session.commit()
        return jsonify({'msg': 'Success'})
    except:
        return jsonify({'msg': 'Role cannot be deleted. Contact our support team for more details'})

@route.route('/role/clear/<id>', methods=['POST'])
@login_required
def clear_role(id):
    user = tblUser.query.get(id)
    user.roles.clear()
    try:
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has cleared role from user:' + user.username, type='Delete', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        return jsonify({'data': 'Success'})
    except:
        return jsonify({'data': 'Faild'})

@route.route('/admin')
@login_required
def admin():
    users = tblUser.query.all()
    roles = tblRole.query.all()
    return render_template('views/admin.html', users=users, roles=roles)

@route.route('/admin/<id>', methods=['POST'])
def get_admin(id):
    User = tblUser.query.get(id)
    json = UserSchema()
    user = json.dump(User)
    return jsonify(user)

@route.route('/admin/create', methods=['POST'])
def create_admin():
    username = request.form['username']
    fullname = request.form['fullname']
    gender = request.form['gender']
    email = request.form['email']
    phone = request.form['phone']
    hometown = request.form['hometown']
    company = request.form['company']
    location = request.form['location']
    status = request.form['status']
    password = request.form['password']
    role = request.form['role']
    if request.form['birthdate'] != '':
        birthdate = datetime.strptime(request.form['birthdate'], '%m/%d/%y')
    else:
        birthdate = None
    user_id = str(uuid4())
    User = tblUser(id=user_id, username=username, firstname=fullname.split(' ')[0], lastname=fullname.split(' ')[1], gender=gender, email=email, birthdate=birthdate, password=bcrypt.generate_password_hash(password).decode('utf-8'), publicId=str(uuid4()))
    try: 
        db.session.add(User)
        db.session.commit()
        if role != '':
            Role = tblRole.query.get(role)
            User.roles.append(Role)
        Profile = tblProfile(id=str(uuid4()), phone=phone, status=status, company=company, location=location, hometown=hometown, createdBy=user_id)
        db.session.add(Profile)
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has created user: '+User.username, type='Created', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        return jsonify({'data': 'Success'})
    except:
        return jsonify({'data': 'Faild'})

@route.route('/admin/change/<id>', methods=['POST'])
def change_admin(id):
    user = tblUser.query.get(id)
    user.username = request.form['username']
    user.firstname = request.form['fullname'].split(' ')[0]
    user.lastname = request.form['fullname'].split(' ')[1]
    user.gender = request.form['gender']
    if request.form['birthdate'] != '':
        user.birthdate = datetime.strptime(request.form['birthdate'], '%Y-%m-%d')

    user.email = request.form['email']
    user.profile[0].status = request.form['status']
    user.profile[0].phone = request.form['phone']
    user.profile[0].hometown = request.form['hometown']
    user.profile[0].company = request.form['company']
    user.profile[0].location = request.form['location']
    if request.form['role'] != '':
        if user.roles:
            user.roles[0] = tblRole.query.get(request.form['role'])
        else:
            user.roles.append(tblRole.query.get(request.form['role']))

    if request.form['password'] != '':
        user.password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
    try:
        Activity = tblActivity(id=str(uuid4()), activity=current_user.username+' has modified user: '+user.username, type='Modify', createdBy=current_user.id)
        db.session.add(Activity)
        db.session.commit()
        return jsonify({'data': 'Success'})
    except:
        return jsonify({'data': 'Faild'})