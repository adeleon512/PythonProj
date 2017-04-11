import flask
from bookmarky import bug_users, bug_bookmarks
from bookmarky.dbutil import db_connect
from contextlib import closing
import urllib

app = flask.Flask(__name__)
app.config.from_pyfile('settings.py')


@app.route('/')
def hello_world():
    if 'auth_user' in flask.session:
        # we have a user
        with db_connect(app) as dbc:
            uid = flask.session['auth_user']
            user = bug_users.get_user(dbc, uid)
            if user is None:
                app.logger.error('invalid user %d', uid)
                flask.abort(400)

            user_marks = bug_bookmarks.get_for_user(dbc, uid)
            return flask.render_template('bug_home.html', user=user,
                                          bookmarks=user_marks)
    else:
        return flask.render_template('bug_login.html')


@app.route('/login', methods=['POST'])
def login():
    username = flask.request.form['user']
    password = flask.request.form['passwd']
    display_name = flask.request.form['display_name']
    e_mail = flask.request.form['e_mail']
    role = flask.request.form['role']
    if username is None or password is None:
        flask.abort(400)
    action = flask.request.form['action']
    if action == 'Log in':
        with closing(db_connect(app)) as dbc:
            uid = bug_users.check_auth(dbc, username, password)
            if uid is not None:
                flask.session['auth_user'] = uid
                return flask.redirect('/', code=303)
            else:
                flask.abort(403)
    elif action == 'Create account':
        with closing(db_connect(app)) as dbc:
            uid = bug_users.create_user(dbc, username, password, display_name,
                                        e_mail, role)
            flask.session['auth_user'] = uid
            return flask.redirect('/', code=303)


@app.route('/create_bug', methods=['GET', 'POST'])
def create_bug():
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        with closing(db_connect(app)) as dbc:
            milestones = bug_bookmarks.get_milestones(dbc)
            developers = bug_bookmarks.get_developers(dbc)
        return flask.render_template('create_bug.html', milestones=milestones,
                                    developers=developers)
    else:
        with closing(db_connect(app)) as dbc:
            bug_bookmarks.create_bug(dbc, uid, flask.request.form)
        return flask.redirect('/', code=303)


@app.route('/add_comment/<int:bid>', methods=['GET', 'POST'])
def add_comment(bid):
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        return flask.render_template('add_comment.html', bug_id = bid)
    else:
        with closing(db_connect(app)) as dbc:
            bug_bookmarks.add_comment(dbc, bid, uid, flask.request.form)
        return flask.redirect('/bug_details/' + str(bid), code=303)

@app.route('/add_hours_worked/<int:bid>', methods=['GET', 'POST'])
def add_hours_worked(bid):
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        return flask.render_template('add_hours_worked.html', bug_id = bid)
    else:
        with closing(db_connect(app)) as dbc:
            print('Test print for else clause')
            bug_bookmarks.add_hours_worked(dbc, bid, uid, flask.request.form)
            print('Test print for else clause, after call')
        return flask.redirect('/bug_details/' + str(bid), code=303)


@app.route('/bug_details/<int:bid>', methods=['GET', 'POST'])
def bug_details(bid):
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        with closing(db_connect(app)) as dbc:
            bug = bug_bookmarks.get_bug(dbc, bid)
            bug_comments = bug_bookmarks.get_bug_comments(dbc, bid)
        return flask.render_template('bug_details.html', bug=bug,
                                     bug_comments = bug_comments)

    #I do not think the 'POST' method is used
    else:
        with closing(db_connect(app)) as dbc:
            bug_bookmarks.get_bugs(dbc, uid, flask.request.form)
        return flask.redirect('/', code=303)


@app.route('/edit_bug/<int:bid>', methods=['GET', 'POST'])
def edit_bug(bid):
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        with closing(db_connect(app)) as dbc:
            bug = bug_bookmarks.get_bug(dbc, bid)
            milestones = bug_bookmarks.get_milestones(dbc)
            developers = bug_bookmarks.get_developers(dbc)
        return flask.render_template('edit_bug.html', bug=bug,
                                     milestones=milestones,
                                     developers=developers)
    else:
        with closing(db_connect(app)) as dbc:
            bug_bookmarks.update_bug(dbc, bid, flask.request.form)
        return flask.redirect('/', code=303)


@app.route('/news_feed', methods=['GET', 'POST'])
def news_feed():
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        with closing(db_connect(app)) as dbc:
            news_comments = bug_bookmarks.get_news_comments(dbc, uid)
        return flask.render_template('news_feed.html', news_comments=news_comments)

    #I do not think the 'POST' method is used
    else:
        with closing(db_connect(app)) as dbc:
            bug_bookmarks.get_bugs(dbc, uid, flask.request.form)
        return flask.redirect('/', code=303)


@app.route('/bug_list', methods=['GET', 'POST'])
def bug_list():
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        with closing(db_connect(app)) as dbc:
            bugs = bug_bookmarks.get_bugs(dbc)
        return flask.render_template('bug_list.html', bugs=bugs)

    #I do not think the 'POST' method is used
    else:
        with closing(db_connect(app)) as dbc:
            bug_bookmarks.get_bugs(dbc, uid, flask.request.form)
        return flask.redirect('/', code=303)

@app.route('/user_profile', methods=['GET', 'POST'])
def user_profile():
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        with closing(db_connect(app)) as dbc:
            user_info = bug_bookmarks.get_user_info.user_info(dbc,uid)
        return flask.render_template('user_profile.html', user_info=user_info)
    else:
        with closing(db_connect(app)) as dbc:
            bug_bookmarks.get_bugs(dbc, uid, flask.request.form)
            return flask.redirect('/', code=303)


@app.route('/edit_user_profile', methods=['GET', 'POST'])
def edit_user_profile():
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        with closing(db_connect(app)) as dbc:
            user_info = bug_bookmarks.get_user_info(dbc, uid)
        return flask.render_template('edit_user_profile.html', user_info=user_info)

    else:
        with closing(db_connect(app)) as dbc:
            bug_bookmarks.edit_user_profile(dbc, uid, flask.request.form)
        return flask.redirect('/user_profile', code=303)

@app.route('/reports/<int:rid>', methods=['GET', 'POST'])
def reports(rid):
    if 'auth_user' in flask.session:
        uid = flask.session['auth_user']
    else:
        flask.abort(403)

    if flask.request.method == 'GET':
        if rid == 1:
            with closing(db_connect(app)) as dbc:
                report_info_1 = bug_bookmarks.get_report_info_1(dbc)
            return flask.render_template('report_1.html',
                                          report_info_1=report_info_1)
        if rid == 2:
            with closing(db_connect(app)) as dbc:
                report_info_2 = bug_bookmarks.get_report_info_2(dbc)
            return flask.render_template('report_2.html',
                                          report_info_2=report_info_2)

        if rid == 3:
            with closing(db_connect(app)) as dbc:
                report_info_3 = bug_bookmarks.get_report_info_3(dbc)
            return flask.render_template('report_3.html',
                                         report_info_3=report_info_3)
    #I do not think the 'POST' method is used
        else:
            with closing(db_connect(app)) as dbc:
                bug_bookmarks.get_bugs(dbc, uid, flask.request.form)
            return flask.redirect('/', code=303)


if __name__ == '__main__':
    app.run()
