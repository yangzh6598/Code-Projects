from flask import Flask, render_template, request, make_response, session, jsonify
import os
import pymysql
from pymysql import IntegrityError
import dbconfig
import time
import pdb


app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'


def get_date():
    return time.strftime("%Y-%m-%d")


def connect():
    conn = pymysql.connect(host=dbconfig.HOST,
                           port=dbconfig.PORT,
                           user=dbconfig.USERNAME,
                           passwd=dbconfig.PASSWORD,
                           db=dbconfig.DB)
    cur = conn.cursor()
    return cur, conn


def add_new_user(form):
    username = form["username"]
    password = form["password"]
    email = form["email"]
    user_type = form["type"]
    insert_user_table = 'INSERT INTO sls4400.User VALUES("{0}", "{1}", "{2}", "{3}")'.format(username, password, email, user_type)
    print (insert_user_table)
    cur, conn = connect()
    cur.execute(insert_user_table)
    conn.commit()
    for row in cur:
        print(row)
    if user_type == "official":
        city = form["city"]
        state = form["state"]
        title = form["title"]
        insert_city_official_table = 'INSERT INTO sls4400.CityOfficial VALUES("{0}", "{1}", "{2}", "{3}", NULL)'.format(username, city, state, title)
        print(insert_city_official_table)
        cur.execute(insert_city_official_table)
        conn.commit()


def build_username_password_query(username, password):
    query = "SELECT * FROM sls4400.User " \
            "WHERE username=" + '"' + username + '"' + \
            " AND password=" + '"' + password + '"'
    return query


def build_get_states_query():
    query = "SELECT DISTINCT state from sls4400.CityState"
    return query


def build_get_cities_query(state="GA"):
    query = "SELECT city from sls4400.CityState where state=" + '"' + state + '"'
    return query


def get_cities(state="GA"):
    if state == "*":
        query = "select city from sls4400.CityState"
        cur, conn = connect()
        cur.execute(query)
        return [row[0] for row in cur]
    cur, conn = connect()
    cur.execute(build_get_cities_query(state))
    return [row[0] for row in cur]


def get_states():
    cur, conn = connect()
    cur.execute(build_get_states_query())
    return [row[0] for row in cur]


@app.route("/getcities")
def get_cities_url():
    state = request.args.get("state")
    return jsonify(get_cities(state))


def check_username_email_uniqueness(username, email):
    errors = []
    cur, conn = connect()
    username_uniqueness_query = "SELECT count(*) FROM sls4400.User WHERE username=" + '"' + username + '"'
    email_uniqueness_query = "SELECT count(*) FROM sls4400.User WHERE email=" + '"' + email + '"'
    cur.execute(username_uniqueness_query)
    num_usernames = cur.fetchone()[0]
    cur.execute(email_uniqueness_query)
    num_emails = cur.fetchone()[0]
    if num_usernames == 1:
        errors.append("A user with this username already exists.")
    if num_emails == 1:
        errors.append("A user with this email already exists.")
    return errors


def check_valid_registration(form):
    errors = []
    if form['password'] != form['cfpassword']:
        errors.append("Passwords do not match.")
    if form['username'] == "":
        errors.append("Username cannot be blank.")
    if len(form["password"]) > 25:
        errors.append("Password must be less than 25 characters.")
    if len(form["username"]) > 25:
        errors.append("Username must be less than 25 characters.")
    if form["email"] == "":
        errors.append("Email cannot be blank.")
    if len(form["email"]) > 50:
        errors.append("Email must be less than 50 characters.")
    if form["password"] == "":
        errors.append("Password cannot be blank.")
    if "type" not in form:
        errors.append("Please select a user type (city official or city scientist).")
    else:
        if form["type"] == "official":
            if form["title"] == "":
                errors.append("Please enter your title if you are registering as a city official.")
    for error in check_username_email_uniqueness(form['username'], form['email']):
        errors.append(error)
    return errors


@app.route("/register", methods=["GET", "POST"])
def register():
    states = get_states()
    cities = get_cities()
    if request.method == "GET":
        if "username" in session:
            return render_homepage_for_user(session["type"])
        else:
            return render_template("register.html", states=states, cities=cities)
    elif request.method == "POST":
        print(request.form)
        errors = check_valid_registration(request.form)
        if len(errors) > 0:
            return render_template("register.html", states=states, cities=cities, errors=errors)
        else:
            add_new_user(request.form)
            return render_template("login.html", title="SLS Home", logged_in=False)


@app.route("/logout", methods=["GET"])
def logout():
    error = "You aren't logged in."
    if "username" in session:
        session.pop("username", None)
        session.pop("email", None)
        session.pop("type", None)
        session.pop("loggedin", None)
        error = "You have been successfully logged out."
    return render_template("login.html", title="SLS Home", error=error)


def city_official_is_approved(username):
    query = 'SELECT approved FROM sls4400.CityOfficial WHERE username="{0}"'.format(username)
    cur, conn = connect()
    cur.execute(query)
    result = cur.fetchone()[0]
    return result


def render_homepage_for_user(type, messages=[]):
    if type == "admin":
        return render_template("adminhome.html",
                               title="SLS-Admin",
                               logged_in=True,
                               admin=True,
                               username=session["username"])
    elif type == "official":
        username = session["username"]
        approved = city_official_is_approved(username)
        if approved == 0 or approved is None:
            return render_template("unapprovedofficial.html",
                                   title="SLS-Official",
                                   logged_in=True,
                                   username=session["username"])
        else:
            return render_template("approvedofficialhome.html",
                                   title="SLS-Official",
                                   logged_in=True,
                                   approved_official=True,
                                   username=session['username'])
    elif type == "scientist":
        return render_template("scientisthome.html",
                               title="SLS-Scientist",
                               logged_in=True,
                               username=session["username"],
                               scientist=True,
                               messages=messages)


def check_unique_locaname(locname):
    cur, conn = connect()
    query = 'SELECT count(*) FROM sls4400.POI WHERE locname="{0}"'.format(locname)
    cur.execute(query)
    count = cur.fetchone()[0]
    if count == 0:
        return True
    return False


def check_valid_poi(form):
    errors = []
    locname = form["locname"]
    zipcode = form["zipcode"]
    city = form["city"]
    state = form["state"]
    if locname == "":
        errors.append("A location name is required.")
    if len(locname) > 150:
        errors.append("Location name is too long.")
    if not check_unique_locaname(locname):
        errors.append("A POI with this name already exists")
    if len(zipcode) != 5:
        errors.append("Please enter a 5 digit zip code")
    try:
        int(zipcode)
    except ValueError:
        errors.append("Only numeric characters are allowed in the zip code.")
    return errors


def add_poi(form):
    locname = form["locname"]
    zipcode = form["zipcode"]
    city = form["city"]
    state = form["state"]
    query = 'insert into sls4400.POI values("{0}", "{1}", 0, NULL, "{2}", "{3}")'.format(locname, zipcode, city, state)
    cur, conn = connect()
    cur.execute(query)
    conn.commit()


def add_data_point_into_database(form):
    cur, conn = connect()
    time = form["time"]
    date = form["date"]
    poiname = form["poiname"]
    type = form["type"]
    value = form["value"]
    datetime = date + " " + time
    query = 'insert into sls4400.DataPoint values("{0}", "{1}", "{2}", NULL, "{3}")'.format(datetime, poiname, value, type)
    print(query)
    try:
        cur.execute(query)
        conn.commit()
        return True
    except IntegrityError:
        return False


def check_data_point_valid(form):
    date = form["date"]
    time = form["time"]
    value = form["value"]
    errors = []
    print( 'date', date)
    if date == "":
        errors.append("Date can't be blank.")
    if time == "":
        errors.append("Time can't be blank.")
    if value == "":
        errors.append("Value can't blank.")
    return errors


def get_pois():
    query = 'select locname from sls4400.POI'
    cur, conn = connect()
    cur.execute(query)
    return [row[0] for row in cur]


def get_pois_full_tuples():
    query = 'select * from sls4400.POI'
    cur, conn = connect()
    cur.execute(query)
    return [row for row in cur]



def get_data_types():
    query = 'select type from sls4400.DataType'
    cur, conn = connect()
    cur.execute(query)
    return [row[0] for row in cur]


@app.route('/adddatapoint', methods=['GET', 'POST'])
def add_data_point():
    if request.method == 'GET':
        return render_template("adddatapoint.html",
                               title="SLS-Add Data Point",
                               username=session["username"],
                               scientist=True,
                               pois=get_pois(),
                               types=get_data_types(),
                               logged_in=True)
    elif request.method == "POST":
        messages = []
        messages.append("Data point successfully added and is pending approval.")
        errors = check_data_point_valid(request.form)
        if len(errors) == 0:
            if add_data_point_into_database(request.form):
                return render_homepage_for_user(session["type"], messages=messages)
            else:
                errors.append("A data point with this POI, time, and date already exists.")
        return render_template("adddatapoint.html",
                               title="SLS-Add Data Point",
                               username=session["username"],
                               scientist=True,
                               pois=get_pois(),
                               types=get_data_types(),
                               errors=errors,
                               logged_in=True)




@app.route('/addlocation', methods=['GET', 'POST'])
def add_location():
    if request.method == 'GET':
        if "type" in session:
            if session["type"] == "scientist":
                return render_template("location.html",
                                       title="SLS-Add Location",
                                       logged_in=True,
                                       username=session["username"],
                                       scientist=True,
                                       states=get_states(),
                                       cities=get_cities())
            else:
                return render_homepage_for_user(session["type"])
        else:
            return render_template("login.html", error="Please login to see this page.")
    elif request.method == "POST":
        errors = check_valid_poi(request.form)
        if len(errors) > 0:
            return render_template("location.html",
                                   title="SLS-Add Location",
                                   logged_in=True,
                                   username=session["username"],
                                   scientist=True,
                                   states=get_states(),
                                   cities=get_cities(),
                                   errors=errors)
        else:
            add_poi(request.form)
            messages = []
            messages.append("POI ({0}) successfully added".format(request.form["locname"]))
            return render_homepage_for_user(session["type"], messages=messages)



@app.route('/', methods=['GET', 'POST'])
def home():
    title = "SLS Home"
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        cur, conn =connect()
        cur.execute(build_username_password_query(username, password))
        if cur.rowcount == 1:
            user = cur.fetchone()
            print(user)
            username = user[0]
            email = user[2]
            type = user[3]
            session["username"] = username
            session["email"] = email
            session["type"] = type
            session["loggedin"] = "true"
            return render_homepage_for_user(session["type"])
        else:
            return render_template("login.html", title=title, error="Invalid Username/Password combination.")
    else:

        if "username" in session:
            return render_homepage_for_user(session["type"])
        else:
            return render_template("login.html",
                                   title=title,
                                   logged_in=False)


def get_pending_data_points():
    query = 'select * from sls4400.DataPoint where approved is NULL'
    cur, conn = connect()
    cur.execute(query)
    results = [row for row in cur]
    return results


def approve_or_reject_data_points(data_points, approve=True):
    for data_point in data_points:
        datetime = data_point.split("|")[0]
        poiname = data_point.split("|")[1]
        query_approve_or_reject = "1" if approve else "0"
        query = 'update sls4400.DataPoint ' \
                'set approved={0} ' \
                'where datetime="{1}" ' \
                'and poiname="{2}"'.format(query_approve_or_reject, datetime, poiname)
        print(query)
        cur, conn = connect()
        cur.execute(query)
        conn.commit()


def approve_or_reject_city_officials(city_officials, approve=True):
    for city_official in city_officials:
        query_approve_or_reject = "1" if approve else "0"
        query = 'update sls4400.CityOfficial ' \
                'set approved={0} ' \
                'where username="{1}"'.format(query_approve_or_reject, city_official)



        print(query)
        cur, conn = connect()
        cur.execute(query)
        conn.commit()


def render_data_points_table_page():
    points = get_pending_data_points()
    return render_template("approvedatapoints.html",
                           title="SLS-Approve Data Points",
                           logged_in=True,
                           admin=True,
                           results=points)


@app.route('/pendingdatapoints', methods=['GET', 'POST'])
def pending_data_points():
    if 'type' in session:
        if request.method == "GET":
            if session["type"] == "admin":
                return render_data_points_table_page()
            else:
                return render_homepage_for_user(session['type'])
        else: #request.form == "POST"
            if "approve_button" in request.form:
                data_points = [key for key in request.form if key != "approve_button"]
                approve_or_reject_data_points(data_points)
                return render_data_points_table_page()
            elif "reject_button" in request.form:
                data_points = [key for key in request.form if key != "reject_button"]
                approve_or_reject_data_points(data_points, approve=False)
                return render_data_points_table_page()
            else:
                render_homepage_for_user(session['type'])
            return str(request.form)
    else:
        return render_template('login.html',
                               title='SLS Home',
                               logged_in=False)


def get_pending_officials():
    query = 'select * from sls4400.CityOfficial natural join sls4400.User where approved is NULL'
    cur, conn = connect()
    cur.execute(query)
    results = [row for row in cur]
    return results


def render_approve_official_page():
    pending_officials = get_pending_officials()
    return render_template("approveofficials.html",
                           title="SLS-Approve Officials",
                           logged_in=True,
                           admin=True,
                           pending_officials=pending_officials)


@app.route('/pendingofficials', methods=["GET", "POST"])
def pending_officials():
    if "type" in session:
        if request.method == "GET":
            if session["type"] == "admin":
                return render_approve_official_page()
            else:
                return render_homepage_for_user(session["type"])
        else: #POST
            if "approve_button" in request.form:
                officials = [key for key in request.form if key != "approve_button"]
                approve_or_reject_city_officials(officials)
                return render_approve_official_page()
            elif "reject_button" in request.form:
                officials = [key for key in request.form if key != "reject_button"]
                approve_or_reject_city_officials(officials, approve=False)
                return render_approve_official_page()
    else:
        return render_template('login.html',
                               title='SLS Home',
                               logged_in=False)


def render_filter_all_pois(pois_filtered=get_pois_full_tuples()):
    return render_template("filtersearch.html",
                           title="SLS-Filter/Search",
                           logged_in=True,
                           approved_official=True,
                           pois=get_pois(),
                           states=get_states(),
                           cities=get_cities(state="*"),
                           pois_full=pois_filtered)


def filter_poi_all_blank(form):
    for key in form:
        if key == 'apply-filter':
            pass
        else:
            if form[key] != "":
                return False
    return True


def check_detail_filter_form_for_errors(form):
    errors = []
    if request.form["time-to"] != "" and request.form["date-to"] == "":
        errors.append("Please fill out a date to if you fill out a time to.")
    if request.form["time-from"] != "" and request.form["date-from"] == "":
        errors.append("Please fill out a date from if you fill out a time from.")
    return errors


def get_filtered_data_points_query(form, location_name):
    query = 'select datetime, poiname, value, type from sls4400.DataPoint where poiname="{0}" and approved=1 '.format(location_name)
    print(query)
    if filter_poi_all_blank(form):
        query += " order by datetime asc"
        return query
    else:
        query += "and "
    conditions = []
    if form["date-from"] != "" and form["time-from"] != "":
        datetime_from = form["date-from"] + " " + form["time-from"]
        conditions.append('datetime>="{0}"'.format(datetime_from))
    if form["date-from"] != "" and form["time-from"] == "":
        conditions.append('datetime>="{0}"'.format(form["date-from"]))
    if form["date-to"] != "" and form["time-to"] != "":
        datetime_to = form["date-to"] + " " + form["time-to"]
        conditions.append('datetime<="{0}"'.format(datetime_to))
    if form["date-to"] != "" and form["time-to"] == "":
        conditions.append('datetime<="{0}"').format["date-to"]
    if form["value-from"] != "":
        conditions.append('value>={0}'.format(form["value-from"]))
    if form["value-to"] != "":
        conditions.append('value<={0}'.format(form["value-to"]))
    if form["type"] != "":
        conditions.append('type="{0}"'.format(form["type"]))

    to_add = " and ".join(conditions)
    query += to_add
    query += " order by datetime asc"
    print(query)
    return query


def get_filtered_pois_query(form):
    query = "select * from sls4400.POI"
    if filter_poi_all_blank(form):
        return query
    else:
        query += " where "
    conditions = []
    if form["city"] != "":
        conditions.append('city="{0}"'.format(form["city"]))
    if form["state"] != "":
        conditions.append('state="{0}"'.format(form["state"]))
    if form["poi"] != "":
        conditions.append('locname="{0}"'.format(form['poi']))
    if form["zipcode"] != "":
        conditions.append('zipcode="{0}"'.format(form['zipcode']))
    if form['date-flagged-to'] != "":
        conditions.append('dateflagged<="{0}"'.format(form['date-flagged-to']))
    if form['date-flagged-from'] != "":
        conditions.append('dateflagged>="{0}"'.format(form['date-flagged-from']))
    if 'flagged' in form:
        if form['flagged'] == "on":
            conditions.append('flag=1')
    to_add = " and ".join(conditions)
    query += to_add
    print(query)
    return query


def get_rows_from_query(query):
    cur, conn = connect()
    cur.execute(query)
    return [row for row in cur]


def get_filtered_pois(query):
    return get_rows_from_query(query)


@app.route('/filter', methods=["GET", "POST"])
def filter():
    if "type" in session:
        if request.method == "GET":
            if session["type"] == "official":
                if city_official_is_approved(session['username']):
                    return render_filter_all_pois(pois_filtered=get_pois_full_tuples())
            return render_homepage_for_user(session["type"])
        else: #POST
            #TODO: handle posted data
            if 'apply-filter' in request.form:
                query = get_filtered_pois_query(request.form)
                results = get_filtered_pois(query)
                return render_filter_all_pois(pois_filtered=results)
            else:
                return render_filter_all_pois(pois_filtered=get_pois_full_tuples())
    else:
        return render_template('login.html',
                               title='SLS Home',
                               logged_in=False)


def get_data_points_for_location(location_name):
    query = 'select datetime, poiname, value, type from sls4400.DataPoint' \
          ' where poiname="{0}" and approved=1 order by datetime asc'.format(location_name)
    print(query)
    cur, conn = connect()
    cur.execute(query)
    return [row for row in cur]


def render_detail_location_template(location_name, data_points_, errors=[], is_flagged=False):
    return render_template("poidetail.html",
                           location_name=location_name,
                           logged_in=True,
                           approved_official=True,
                           title="SLS-POI Detail",
                           types=get_data_types(),
                           data_points=data_points_,
                           errors=errors,
                           flagged=is_flagged)


def flag_unflag_location(location_name, flag=True):
    query = None
    if flag:
        flag_value = 1
        query = 'update sls4400.POI set flag={0}, dateflagged="{1}" where locname="{2}"'.format(flag_value, get_date(), location_name)
    else:
        query = 'update sls4400.POI set flag=0, dateflagged=NULL where locname="{0}"'.format(location_name)
    cur, conn = connect()
    cur.execute(query)
    conn.commit()


def location_is_flagged(location_name):
    query = 'select flag from sls4400.POI where locname="{0}"'.format(location_name)
    cur, conn = connect()
    cur.execute(query)
    flag = cur.fetchone()[0]
    return flag == 1


@app.route('/detail/<location_name>', methods=["GET", "POST"])
def detail(location_name):
    flagged = location_is_flagged(location_name)
    print(location_nam, "flagged status", flagged)
    if "type" in session:
        if request.method == "GET":
            if session["type"] == "official":
                if city_official_is_approved(session['username']):
                    return render_detail_location_template(location_name, get_data_points_for_location(location_name), is_flagged=flagged)
            return render_homepage_for_user(session["type"])
        else: #POST
            errors = check_detail_filter_form_for_errors(request.form)
            if len(errors) != 0:
                return render_detail_location_template(location_name, get_data_points_for_location(location_name), errors=errors, is_flagged=flagged)
            if "apply-filter" in request.form:
                query = get_filtered_data_points_query(request.form, location_name)
                results = get_rows_from_query(query)
                return render_detail_location_template(location_name, results, is_flagged=flagged)
            if "flag" in request.form:
                flag_unflag_location(location_name, True)
                flagged = location_is_flagged(location_name)
                return render_detail_location_template(location_name, get_data_points_for_location(location_name), is_flagged=flagged)
            if "unflag" in request.form:
                flag_unflag_location(location_name, False)
                flagged = location_is_flagged(location_name)
                return render_detail_location_template(location_name, get_data_points_for_location(location_name), is_flagged=flagged)
            else:
                return render_detail_location_template(location_name, get_data_points_for_location(location_name), is_flagged=flagged)
    else:
        return render_template('login.html',
                               title='SLS Home',
                               logged_in=False)


def get_poi_report_data():
    query = 'select * from \
        (select t1.locname, t1.city, t1.state, t1.zipcode, t1.avaq, t1.minaq, t1.maxaq, t2.avmold, t2.minmold, t2.maxmold, t1.flag from \
        (select locname, city, state, zipcode, flag, dateflagged, avg(value) as avaq, min(value) as minaq, max(value) as maxaq  from sls4400.DataPoint join sls4400.POI on locname=poiname where type="Air Quality" group by locname) t1 \
        left outer join \
        (select locname, city, state, zipcode, flag, dateflagged, avg(value) as avmold, min(value) as minmold, max(value) as maxmold from sls4400.DataPoint join sls4400.POI on locname=poiname where type="Mold" group by locname) t2  \
        on t1.locname=t2.locname \
        union \
        select t4.locname, t4.city, t4.state, t4.zipcode, t3.avaq, t3.minaq, t3.maxaq, t4.avmold, t4.minmold, t4.maxmold, t3.flag from \
        (select locname, city, state, zipcode, flag, dateflagged, avg(value) as avaq, min(value) as minaq, max(value) as maxaq from sls4400.DataPoint join sls4400.POI on locname=poiname where type="Air Quality" group by locname) t3 \
        right outer join \
        (select locname, city,state, zipcode, flag, dateflagged, avg(value) as avmold, min(value) as minmold, max(value) as maxmold from sls4400.DataPoint join sls4400.POI on locname=poiname where type="Mold" group by locname) t4  \
        on t3.locname=t4.locname) z1 \
        join \
        (select poiname, count(*) from sls4400.DataPoint group by poiname) z2 \
        on locname=poiname'
    cur, conn = connect()
    cur.execute(query)
    return [row for row in cur]


@app.route('/poireport')
def poi_report():
    if "type" in session:
        if session["type"] == "official":
            if city_official_is_approved(session["username"]):
                data_report = get_poi_report_data()
                for data_point in data_report:
                    print(data_point)
                return render_template("poireport.html",
                                       logged_in=True,
                                       approved_official=True,
                                       title="SLS-POI Report",
                                       data_points=data_report)
        return render_homepage_for_user(session["type"])
    else:
        return render_template("login.html", title="SLS Home", logged_in=False)


if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
