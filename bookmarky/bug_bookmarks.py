import flask
import psycopg2
import sys

def create_bug(dbc, uid, form):
    with dbc, dbc.cursor() as cur:
        bug_title = form['bug_title'].strip()
        bug_details = form['bug_details'].strip()
        creator = uid
        #assignee 3 is the default user with display name=unassigned
        assignee = 3
        tag_text = ''
        status = 'Open'
        bug_priority = form['bug_priority'].strip()
        milestone_id = form['milestone'].strip()

        cur.execute('''
            INSERT INTO bug
              (bug_title, bug_details, creator, assignee,
               tag_text, status, bug_priority, milestone_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING bug_id
        ''', (bug_title, bug_details, creator, assignee,tag_text,
              status, bug_priority, milestone_id))
        bid = cur.fetchone()[0]

        tags = form['tags'].split(',')
        for tag in tags:
            cur.execute('''
                INSERT INTO bug_tag (bug_id, tag) VALUES (%s, %s)
            ''', (bid, tag.strip().lower()))


def update_bug(dbc, bid, form):
    ntries = 1
    while ntries < 5:
        try:
            with dbc:
                with dbc.cursor() as cur:

                    cur.execute('''
                      SELECT bug_id FROM bug
                      WHERE bug_id = %s
                    ''', (bid,))
                    row = cur.fetchone()
                    if row is None:
                        flask.abort(403)

                    bug_title = form['bug_title'].strip()
                    if not bug_title:
                        bug_title = None
                    bug_details = form['bug_details'].strip()
                    if not bug_details:
                        bug_details = None
                    bug_priority = form['bug_priority']
                    if not bug_priority:
                        bug_priority = None
                    milestone_id = form['milestone']
                    if not milestone_id:
                        milestone_id = None
                    assignee = form['assignee'].strip()
                    if not assignee:
                        assignee = None
                    status = form['status'].strip()
                    if not status:
                        status = None

                    cur.execute('''
                        UPDATE bug
                        SET bug_title = %s, bug_details = %s,
                            bug_priority = %s, milestone_id = %s,
                            assignee = %s, status = %s
                        WHERE bug_id = %s
                    ''', (bug_title, bug_details, bug_priority,
                          milestone_id, assignee, status, bid))


                    ##tag items
                    cur.execute('''
                        SELECT tag FROM bug_tag WHERE bug_id = %s
                    ''', (bid,))
                    old_tags = []
                    for tag, in cur:
                        old_tags.append(tag)
                    tags = [t.strip().lower() for t in form['tags'].split(',')]
                    for tag in tags:
                        if tag not in old_tags:
                            cur.execute('''
                              INSERT INTO bug_tag (bug_id, tag) VALUES (%s, %s)
                            ''', (bid, tag))
                    for tag in old_tags:
                        if tag not in tags:
                            cur.execute('''
                              DELETE FROM bug_tag
                              WHERE bug_id = %s AND tag = %s
                            ''', (bid, tag))
                return
        except psycopg2.DatabaseError as dbe:
            print("commit error: {}".format(dbe), file=sys.stderr)
            dbc.rollback()
            ntries += 1

    flask.abort(500)


def get_for_user(dbc, uid):
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT bookmark_id, tag
            FROM bookmark JOIN bm_tag USING (bookmark_id)
            WHERE owner_id = %s
        ''', (uid,))
        tag_map = {}
        for bid, tag in cur:
            if bid in tag_map:
                tag_map[bid].append(tag)
            else:
                tag_map[bid] = [tag]

        cur.execute('''
            SELECT bookmark_id, url, COALESCE(title, url),
             notes, create_time
            FROM bookmark
            WHERE owner_id = %s
            ORDER BY create_time DESC
        ''', (uid,))
        marks = []
        for id, url, title, notes, time in cur:
            marks.append({'id': id, 'url': url, 'title': title,
                          'notes': notes, 'create_time': time,
                          'tags': tag_map.get(id, [])})
        return marks


def get_milestones(dbc):
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT milestone_id, milestone_title, target_date
            FROM milestone
            ORDER BY target_date
        ''')
        milestones = []
        for milestone_id, milestone_title, target_date in cur:
            milestones.append({'milestone_id': milestone_id,
                               'milestone_title': milestone_title,
                               'target_date': target_date})
        return milestones


def get_developers(dbc):
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT user_id, display_name
            FROM bug_user
            WHERE role LIKE('Developer')
            ORDER BY display_name
        ''')
        developers = []
        for user_id, display_name in cur:
            developers.append({'user_id': user_id,
                               'display_name': display_name})
        return developers

def add_comment(dbc, bid, uid, form):
    with dbc, dbc.cursor() as cur:
        comment_text = form['comment_text'].strip()

        cur.execute('''
            INSERT INTO comment
              (comment_author, bug_id, comment_text)
            VALUES (%s, %s, %s)
            RETURNING comment_id
        ''', (uid, bid, comment_text))

def get_bug_comments(dbc,bid):
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT comment_id, comment_date,
                   comment_text, display_name
            FROM comment
            JOIN bug_user ON(comment.comment_author = bug_user.user_id)
            WHERE comment.bug_id = %s
            ORDER BY comment_date DESC
        ''', (bid,))
        bug_comments = []
        for (comment_id, comment_date,
             comment_text, display_name) in cur:
            bug_comments.append({'comment_id': comment_id,
                                 'comment_date': comment_date,
                                 'comment_text': comment_text,
                                 'display_name': display_name})
        return bug_comments


def get_news_comments(dbc,uid):
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT comment_id, comment_date,
                   comment_text, display_name
            FROM comment
            JOIN bug_user ON(comment.comment_author=bug_user.user_id)
            JOIN bug USING(bug_id)
            LEFT OUTER JOIN subscription USING(bug_id)
            WHERE bug.creator = %s
               OR bug.assignee = %s
               OR subscription.user_id = %s
            ORDER BY comment_date DESC
        ''', (uid, uid, uid))
        news_comments = []
        for (comment_id, comment_date,
             comment_text, display_name) in cur:
            news_comments.append({'comment_id': comment_id,
                                  'comment_date': comment_date,
                                  'comment_text': comment_text,
                                  'display_name': display_name})
        return news_comments


def add_hours_worked(dbc, bid, uid, form):
    print('in add_hours_worked - before with dbc')
    with dbc, dbc.cursor() as cur:
        print('in add_hours_worked - after with dbc')

        hours_worked = form['hours_worked'].strip()
        print('hours worked = ')
        cur.execute('''
            INSERT INTO hours
              (user_id, bug_id, hours_worked)
            VALUES (%s, %s, %s)
            RETURNING hours_id
        ''', (uid, bid, hours_worked))


def get_bugs(dbc):
    with dbc, dbc.cursor() as cur:

        #get all tags
        cur.execute('''
            SELECT bug_id, tag
            FROM bug JOIN bug_tag USING (bug_id)
        ''')
        tag_map = {}
        for bid, tag in cur:
            if bid in tag_map:
                tag_map[bid].append(tag)
            else:
                tag_map[bid] = [tag]

        #get all bugs
        cur.execute('''
            SELECT bug_id, bug_title, bug_details, creator,creation_date,
                   assignee, assigned_date, tag_text, status, close_date,
                   bug_priority, milestone_title, target_date
            FROM bug
            JOIN milestone USING(milestone_id)
            ORDER BY creation_date DESC
        ''')

        bugs = [{'bug_id': bug_id, 'bug_title': bug_title,
                 'bug_details': bug_details, 'creator': creator,
                 'creation_date': creation_date, 'assignee': assignee,
                 'assigned_date': assigned_date, 'tag_text': tag_text,
                 'status': status, 'close_date': close_date,
                 'bug_priority': bug_priority,
                 'milestone_title': milestone_title,
                 'target_date': target_date, 'tags': tag_map.get(bug_id, [])}
                for (bug_id, bug_title, bug_details, creator, creation_date,
                     assignee, assigned_date, tag_text, status, close_date,
                     bug_priority, milestone_title, target_date) in cur]

        return bugs


def get_bug(dbc, bid):
    with dbc, dbc.cursor() as cur:

        query ='''
            SELECT bug_id, bug_title, bug_details, creator,creation_date,
                   assignee, assigned_date, tag_text, status, close_date,
                   bug_priority, milestone_id, milestone_title, target_date
            FROM bug
            JOIN milestone USING(milestone_id)
            WHERE bug_id = %s'''

        cur.execute(query, (bid,))

        row = cur.fetchone()
        if row is None:
            return None

        (bug_id, bug_title, bug_details, creator, creation_date,
            assignee, assigned_date, tag_text, status, close_date,
            bug_priority, milestone_id, milestone_title, target_date) = row
        bug = {'bug_id': bug_id, 'bug_title': bug_title,
               'bug_details': bug_details, 'creator': creator,
               'creation_date': creation_date, 'assignee': assignee,
               'assigned_date': assigned_date, 'tag_text': tag_text,
               'status': status, 'close_date': close_date,
               'bug_priority': bug_priority,
               'milestone_id': milestone_id,
               'milestone_title': milestone_title,
               'target_date': target_date, 'tags': []}

        cur.execute('''
            SELECT tag FROM bug_tag WHERE bug_id = %s
        ''', (bid,))
        for tag, in cur:
            bug['tags'].append(tag)

        return bug

def user_info(dbc, uid):
    with dbc,dbc.cursor() as cur:
        cur.execute('''
            SELECT user_id, user_name, pw_hash, display_name, e-mail, role
            FROM bug_user
            WHERE user_id = %s
            ''', (uid,))

    row = cur.fetchone()
    if row is None:
        return None
    (user_id, user_name, pw_hash, display_name, e_mail, role) = row

    user_info = {'user_id': user_id, 'user_name': user_name, 'pw_hash':pw_hash, 'display_name': display_name,
                 'e-mail':e_mail, 'role': role}

    return user_info
def update_user_info(dbc, uid, form):
    ntries = 1
    while ntries < 5:
        try:
            with dbc:
                with dbc.cursor() as cur:

                    cur.execute('''
                      SELECT user_id FROM bug
                      WHERE user_id = %s
                    ''', (uid,))
                    row = cur.fetchone()
                    if row is None:
                        flask.abort(403)

                    user_name = form['user_name'].strip()
                    if not user_name:
                        user_name = None
                    display_name = form['display_name'].strip()
                    if not display_name:
                        display_name = None
                    e_mail = form['e-mail'].srtip()
                    if not e_mail:
                        e_mail = None
                    role = form['role'].strip()
                    if not role:
                        role = None

                    cur.execute('''
                        UPDATE User
                        SET user_name = %s, display_name = %s,
                            e_mail = %s, role = %s,
                        WHERE user_id = %s
                    ''', (user_name, display_name, e_mail,
                          role, uid))

                return
        except psycopg2.DatabaseError as dbe:
            print("commit error: {}".format(dbe), file=sys.stderr)
            dbc.rollback()
            ntries += 1

    flask.abort(500)


def get_report_info_1(dbc):
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT bug_id, bug_title, milestone_title, SUM(hours_worked)
            FROM  milestone
            LEFT OUTER JOIN  bug USING (milestone_id)
            LEFT OUTER JOIN  hours USING(bug_id)
            GROUP BY bug_id, bug_title, milestone_title
            ORDER BY milestone_target_date''')

        row = cur.fetchone()
        if row is None:
            return None

        reports = []

        for (bug_id, bug_title, milestone_title, hours_worked) in cur:
            reports.append({'bug_id': bug_id, 'bug_title': bug_title, 'milestone_title': milestone_title,
                            'hours_worked': hours_worked})

        return reports

def get_report_info_2(dbc):
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT user_id, user_name, milestone_title, SUM(hours_worked)
            FROM  milestone
            LEFT OUTER JOIN  bug USING (milestone_id)
            LEFT OUTER JOIN  hours USING(bug_id)
            JOIN  bug_user USING(user_id)
            GROUP BY user_id,user_name, milestone_title
            ORDER BY milestone_target_date
            ''')

        row = cur.fetchone()
        if row is None:
            return None

        reports = []

        for (user_id, user_name, milestone_title, hours_worked) in cur:
            reports.append({'user_id': user_id, 'user_name': user_name, 'milestone_title': milestone_title,
                            'hours_worked': hours_worked})

        return reports

def get_report_info_3(dbc):
    with dbc, dbc.cursor() as cur:
        cur.execute('''
            SELECT milestone_title, target_date, COALESCE(Open,0) AS Open, COALESCE(Ready_for_Testing,0) AS
            Ready_for_Testing, COALESCE(Testing,0) AS Testing, COALESCE(Ready_for_Deployment,0) AS Ready_for_Deployment
            FROM milestone
            LEFT OUTER JOIN (SELECT milestone_id,COUNT(*) AS Open
            FROM bug
            WHERE status = 'Open'
            GROUP BY milestone_id)
            USING (milestone_id)
            LEFT OUTER JOIN (SELECT milestone_id,COUNT(*) AS Ready_for_Testing
            FROM bug
            WHERE status = 'Ready_for_Testing'
            GROUP BY milestone_id)
            USING (milestone_id)
            LEFT OUTER JOIN (SELECT milestone_id,COUNT(*) AS Testing
            FROM bug
            WHERE status = 'Testing'
            GROUP BY milestone_id)
            USING (milestone_id)
            LEFT OUTER JOIN (SELECT milestone_id,COUNT(*) AS Ready_for_Deployment
            FROM bug
            WHERE status = 'Ready_for_Deployment'
            GROUP BY milestone_id)
            USING (milestone_id)
            ORDER BY milestone_id;
            ''')

        row = cur. fetchone()
        if row is None:
            return None


        reports = []

        for (milestone_title, target_date, Open, Ready_for_Testing, Testing, Ready_for_Deployment) in cur:
            reports.append({'milestone_title': milestone_title, 'target_date': target_date, 'Open': Open,
                            'Ready_for_Testing': Ready_for_Testing, 'Testing': Testing,
                            'Ready_for_Deployment': Ready_for_Deployment})

        return reports