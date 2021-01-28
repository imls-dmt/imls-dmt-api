from flask import Flask, request, redirect, url_for, render_template, make_response
import pysolr
import json
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import drupal_hash_utility
from docstring_parser import parse
import requests
from weasyprint import HTML
from datetime import date
from datetime import datetime
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
import uuid
import threading
import time
import random
import string
import smtplib
from email.message import EmailMessage
from flask_oauthlib.provider import OAuth2Provider
from oauthlib.oauth2 import WebApplicationClient, BackendApplicationClient
from requests_oauthlib import OAuth2Session
from feedgen.feed import FeedGenerator

# Create flask app
app = Flask(__name__)

def randomString(stringLength=8):
    letters = string.hexdigits
    return ''.join(random.choice(letters) for i in range(stringLength))

# Pull config info from file
app.config.from_object('dmtconfig.DevConfig')

#Create db object. This will be used for all MySQL actions in this app.
db = SQLAlchemy(app)

#Create user classes manualy as we are not using standard sqlalchemy any more
class Learningresources(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    value = db.Column(db.String(16777215))

class Taxonomies(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    value = db.Column(db.String(16777215))
class Users(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    value = db.Column(db.String(16777215))

class Feedback(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    value = db.Column(db.String(16777215))

class Tokens(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(16777215))
    date = db.Column(db.DateTime)
    uuid = db.Column(db.String(40))



resources_facets = ["facet_author_org.name", "facet_subject", "facet_keywords", "facet_license", "facet_usage_info", "facet_publisher",
                    "facet_accessibility_features.name","facet_language_primary", "facet_languages_secondary", "facet_ed_frameworks.name","facet_author_names", "facet_ed_frameworks.nodes.name", "facet_target_audience", "facet_lr_type", "facet_purpose", "facet_media_type","facet_access_cost"]
# Create a pysolr object for accessing the "learningresources" and "users" index
resources = pysolr.Solr(
    app.config["SOLR_ADDRESS"]+"learningresources/", timeout=10)
users = pysolr.Solr(app.config["SOLR_ADDRESS"]+"users/", timeout=10)
taxonomies = pysolr.Solr(app.config["SOLR_ADDRESS"]+"taxonomies/", timeout=10)
timestamps = pysolr.Solr(app.config["SOLR_ADDRESS"]+"timestamps/", timeout=10)
feedback = pysolr.Solr(app.config["SOLR_ADDRESS"]+"feedback/", timeout=10)
# flask_login implementation.
login_manager = LoginManager()
login_manager.init_app(app)

# Drupal hash utility as we will continue to use Drupal hashes.
drash = drupal_hash_utility.DrupalHashUtility()


##############################
#Shared Functions and classes#
##############################
###################
#Admin Functions###
###################

def reindex():

    lrcount=0
    returnj= json.loads('{"result":{}}')

    Learning_Resources_IDs_count=db.session.query(Learningresources).count()
    rescount=resources.search("*:*",rows=0)
    if rescount.raw_response['response']['numFound']==Learning_Resources_IDs_count:
        resources.delete(q='*:*')
        test = resources.commit()
        Learning_Resources_IDs_res=db.session.query(Learningresources).all()
        Learning_Resources_JSON=[]
        for doc in Learning_Resources_IDs_res:
            Learning_Resources_JSON.append(json.loads(doc.value))
            lrcount=lrcount+1
        resources.add(Learning_Resources_JSON)
        test = resources.commit()
        res=resources.search("*:*",rows=0)
        if res.raw_response['response']['numFound']==lrcount:
            returnj['result']['learning_resources']={"success":True,"count":lrcount}
        else:
            returnj['result']['learning_resources']={"success":False,"solrcount":res.raw_response['response']['numFound'],"sqlcount":lrcount}
    else:
        returnj['result']['learning_resources']={"success":False,"solrcount":rescount.raw_response['response']['numFound'],"sqlcount":Learning_Resources_IDs_count}
    
    lrcount=0
    Users_IDs_count=db.session.query(Users).count()
    rescount=users.search("*:*",rows=0)
    if rescount.raw_response['response']['numFound']==Users_IDs_count: 
        users.delete(q='*:*')
        test = users.commit()
        Users_IDs_res=db.session.query(Users).all()
        Users_IDs_JSON=[]
        for doc in Users_IDs_res:
            Users_IDs_JSON.append(json.loads(doc.value))
            lrcount=lrcount+1
        users.add(Users_IDs_JSON)
        test = users.commit()
        res=users.search("*:*",rows=0)
        if res.raw_response['response']['numFound']==lrcount:
            returnj['result']['users']={"success":True,"count":lrcount}
        else:
            returnj['result']['users']={"success":False,"solrcount":res.raw_response['response']['numFound'],"sqlcount":lrcount}
    else:
        returnj['result']['learning_resources']={"success":False,"solrcount":rescount.raw_response['response']['numFound'],"sqlcount":Users_IDs_count}


    lrcount=0
    Taxonomies_IDs_count=db.session.query(Taxonomies).count()
    rescount=taxonomies.search("*:*",rows=0)
    if rescount.raw_response['response']['numFound']==Taxonomies_IDs_count: 
        taxonomies.delete(q='*:*')
        test = taxonomies.commit()
        Taxonomies_IDs_res=db.session.query(Taxonomies).all()
        Taxonomies_IDs_JSON=[]
        for doc in Taxonomies_IDs_res:
            Taxonomies_IDs_JSON.append(json.loads(doc.value))
            lrcount=lrcount+1
        taxonomies.add(Taxonomies_IDs_JSON)
        test = taxonomies.commit()
        res=taxonomies.search("*:*",rows=0)
        if res.raw_response['response']['numFound']==lrcount:
            returnj['result']['taxonomies']={"success":True,"count":lrcount}
        else:
            returnj['result']['taxonomies']={"success":False,"solrcount":res.raw_response['response']['numFound'],"sqlcount":lrcount}
    else:
        returnj['result']['learning_resources']={"success":False,"solrcount":rescount.raw_response['response']['numFound'],"sqlcount":Taxonomies_IDs_count}



    return returnj


def strip_version(doc):
    doc.pop('_version_', None)
    return doc



def append_searchstring(searchstring, request, name):
    """ 
    Appends searchstring for most text searches.

    Parameters: 

        searcstring (str): Existing search string.

        request (request):  The full request made to a route.

        name (str): The name of the parameter we wish to append to the string.

    Returns: 
    str: Either the appended search string or the original if the validation fails. 
    """
    if request.args.get(name):
        if ":" not in request.args.get(name):
            return searchstring+" AND "+name+":"+request.args.get(name)
        else:
            return searchstring
    else:
        return searchstring


class User(UserMixin):
    """ 
    Simple user class used for authentication and authorization. 
    """

    def __init__(self, id, groups, name):
        self.id = id
        self.groups = groups
        self.name = name


# Callback for login_user
@login_manager.user_loader
def load_user(user_id):
    """ 
    Function used as a callback when login_user is called.
    Parameters: 

    user_id (UUID): ID of user.

    Returns:
        User object or None
    """
    userobj = users.search("id:\""+user_id+"\"", rows=1)
    for user in userobj:
        user.pop('_version_', None)
        user.pop('hash', None)
        return User(user['id'], user['groups'], user['name'])
    return None


# internal user with hash
def get_user(user_name):
    """
    Internal function for building a user object with hash from a given username.
    Parameters: 

        user_name (str): username of valid user.

    Returns:
        User object with hash.
    """
    userobj = users.search("name:\""+user_name+"\"", rows=1)
    for user in userobj:
        user.pop('_version_', None)
        return user
    return None
# Format Solr Return for end user:


def normalize_result(result, template):
    for key in result.keys():
        if key in template.keys():
            template[key] = result[key]
    return template

def insert_new_resource(j):
    #TODO update all facets
    j['id']=str(uuid.uuid4())
    db.session.add(Learningresources(id = j['id'], value=json.dumps(j)))
    try:
        db.session.commit()
    except Exception as err:
        db.session.rollback()
        db.session.flush()
        return({"status":"fail","error":str(err)})
    try:
        resources.add([j])
        test = resources.commit()
        add_timestamp(j['id'],"submit",current_user,request)
    except Exception as solrerr:
        db_session.rollback()
        db_session.flush()
        return({"status":"fail","error":str(solrerr)})
    return({"status":"success","error":None})

def update_resource(j):
    db.session.query(Learningresources).filter(Learningresources.id == j['id']).update({Learningresources.value:json.dumps(j)}, synchronize_session = False)
    #TODO update all facets.
    result1=resources.search("id:"+j['id'], rows=1)
    status="update"
    if j['status'] != result1.docs[0]["status"]:
        if j['status']==1:
            status="publish"
        else:
            j['status']=0 #set to 0 in case of funny business.
            status="un-publish"

    try:
        
        resources.add([j])
        resources.commit()
        db.session.commit()
        add_timestamp(j['id'],status,current_user,request)
    except Exception as err:
        db.session.rollback()
        db.session.flush()
        return({"status":"fail","error":str(err)})
    return({"status":"success","error":None})

def get_score(results,uuid):
    score=None
    for res in results:
        if res['id']==uuid:
            score=res['score']
    return score

def format_resource_jsonld_fromdb(results,sqlresults):
    returnval = json.loads('{ "documentation":"'+request.host_url +
                           'api/resources/documentation.html","results":[], "facets":{}}')
    for solrres in results:

        for result in sqlresults:
            returnjsonresult=json.loads(result.value)
            list_keys = list(returnjsonresult.keys())

            for k in list_keys:
                if k.startswith('facet_'):
                    returnjsonresult.pop(k)

            if returnjsonresult["id"]==solrres['id']:
                newobj={"@context": "http://schema.org/","@type": "CreativeWork",}
                newobj["name"]=returnjsonresult['title']
                newobj["identifier"]=returnjsonresult["id"]
                returnval['results'].append(newobj)

    if "facet_fields" in results.facets.keys():
        for rf in resources_facets:
            rfobject = {}
            if rf in results.facets['facet_fields'].keys():
                for value, number in zip(results.facets['facet_fields'][rf][0::2], results.facets['facet_fields'][rf][1::2]):
                    if number > 0:
                        rfobject[value] = number
            returnval['facets'][rf.replace('facet_', '')] = rfobject
    returnval['hits-total'] = results.hits
    returnval['hits-returned'] = len(results)
    return returnval

def format_resource_fromdb_summary(results):
    returnval = json.loads('{ "documentation":"'+request.host_url +
                           'api/resources/documentation.html","results":[], "facets":{}}')
    ids=[]
    for solrres in results:
        ids.append(solrres['id'])
    returnval['results']=ids
    if "facet_fields" in results.facets.keys():
        for rf in resources_facets:
            rfobject = {}
            if rf in results.facets['facet_fields'].keys():
                for value, number in zip(results.facets['facet_fields'][rf][0::2], results.facets['facet_fields'][rf][1::2]):
                    if number > 0:
                        rfobject[value] = number
            returnval['facets'][rf.replace('facet_', '')] = rfobject
    returnval['hits-total'] = results.hits
    returnval['hits-returned'] = len(results)
    return returnval

def format_resource_fromdb(results,sqlresults):
    lrtemplate=temlate_doc('learningresources')
    returnval = json.loads('{ "documentation":"'+request.host_url +
                           'api/resources/documentation.html","results":[], "facets":{}}')
    for solrres in results:

        for result in sqlresults:
            returnjsonresult=json.loads(result.value)
            list_keys = list(returnjsonresult.keys())

            for k in list_keys:
                if k.startswith('facet_'):
                    returnjsonresult.pop(k)
            if returnjsonresult["id"]==solrres['id']:
                returnjsonresult['score']=get_score(results,returnjsonresult['id'])
                returnval['results'].append(returnjsonresult)

    if "facet_fields" in results.facets.keys():
        for rf in resources_facets:
            rfobject = {}
            if rf in results.facets['facet_fields'].keys():
                for value, number in zip(results.facets['facet_fields'][rf][0::2], results.facets['facet_fields'][rf][1::2]):
                    if number > 0:
                        rfobject[value] = number
            returnval['facets'][rf.replace('facet_', '')] = rfobject
    returnval['hits-total'] = results.hits
    returnval['hits-returned'] = len(results)
    return returnval

def format_resource(results):
    returnval = json.loads('{ "documentation":"'+request.host_url +
                           'api/resources/documentation.html","results":[], "facets":{}}')
    for result in results:
        result.pop('_version_', None)
        result.pop('status', None)
        list_keys = list(result.keys())
        for k in list_keys:
            if k.startswith('facet_'):
                result.pop(k)
        result = normalize_result(result, temlate_doc('learningresources'))
        if "ed_framework" in result.keys():
            result['frameworks']={}
            for framework in result['ed_framework']:
                result['frameworks'][framework]=[]
                if framework=="DataONE Education Modules":
                    if "ed_framework_dataone" in result.keys():
                        for node in result["ed_framework_dataone"]:
                            result['frameworks'][framework].append(node)
                if framework=="FAIR Data Principles":
                    if "ed_framework_fair" in result.keys():
                        for node in result["ed_framework_fair"]:
                            result['frameworks'][framework].append(node)
                if framework=="ESIP Data Management for Scientists Short Course":
                    if "ed_framework_esip" in result.keys():
                        for node in result["ed_framework_esip"]:
                            result['frameworks'][framework].append(node)
                if framework=="USGS Science Support Framework":
                    if "ed_framework_usgs" in result.keys():
                        for node in result["ed_framework_usgs"]:
                            result['frameworks'][framework].append(node)
        if "author_firstnames" in result.keys():
            result['authors']=[]
            for i in range(len(result["author_firstnames"])):
                authorobject = json.loads('{}')
                authorobject['givenName']=result["author_firstnames"][i]
                authorobject['familyName']=result["author_lastnames"][i]
                result['authors'].append(authorobject)
        if "contributors.givenName" in result.keys():
            result['contributors'] = []
            if result["contributors.givenName"]:
                for i in range(len(result["contributors.givenName"])):
                    contributor = json.loads('{}')
                    contributor['givenName'] = result["contributors.givenName"][i]
                    if "contributors.lastname" in result.keys():
                        contributor['familyName'] = result["contributors.familyName"][i]
                    if "contributors.type" in result.keys():
                        if len(result["contributors.type"])>0:
                            contributor['type'] = result["contributors.type"][i]
                    result['contributors'].append(contributor)
        if "contributor_orgs_name" in result.keys():
            result['contributor_orgs'] = []
            for i in range(len(result["contributor_orgs_name"])):
                contributor = json.loads('{}')
                contributor['name'] = result["contributor_orgs_name"][i]

                if "contributor_orgs_type" in result.keys():
                    if len(result["contributor_orgs_type"])>0:
                        contributor['type'] = result["contributor_orgs_type"][i]

                result['contributor_orgs'].append(contributor)
        result.pop('contributor_orgs_type', None)
        result.pop('author_firstnames', None)
        result.pop('author_lastnames', None)
        result.pop('contributor_orgs_name', None)
        result.pop('contributors.firstname', None)
        result.pop('contributors.lastname', None)
        result.pop('contributors.type', None)
        result.pop('ed_framework', None)
        result.pop('ed_framework_dataone', None)
        result.pop('ed_framework_esip', None)
        result.pop('ed_framework_fair', None)
        result.pop('ed_framework_usgs', None)

        returnval['results'].append(result)
    if "facet_fields" in results.facets.keys():
        for rf in resources_facets:
            rfobject = {}
            if rf in results.facets['facet_fields'].keys():
                for value, number in zip(results.facets['facet_fields'][rf][0::2], results.facets['facet_fields'][rf][1::2]):
                    if number > 0:
                        rfobject[value] = number
            returnval['facets'][rf.replace('facet_', '')] = rfobject
    returnval['hits-total'] = results.hits
    returnval['hits-returned'] = len(results)
    return returnval

# Documentation generation


def temlate_doc(collection_name):
    """
    Internal function for building template doc from schema.
    Parameters: 

        collection_name (str): name of a collection.

    Returns:
        json document
    """
    template = json.loads("{}")
    r = requests.get(app.config["SOLR_ADDRESS"] +
                     collection_name+"/schema?wt=json")
    if r.json():
        for field in r.json()['schema']['fields']:
            if not field['name'].startswith(('_', 'facet_')):
                if 'multiValued' in field.keys():
                    if field['multiValued']:
                        template[field['name']] = []
                    else:
                        template[field['name']] = None
                else:
                    template[field['name']] = []
    return template
# Documentation generation


def generate_documentation(docstring, document, request, jsonexample=False):
    request_rule = request.url_rule
    """
    Internal function for building documentation from docstring
    Parameters: 

        docstring (str): docstring with api lines.

    Returns:
        HTML or Markdown
    """
    if docstring is None:
        return "Documentation not yet implemented for this route."
    current_route = ""
    docjson = json.loads('{"methods":{}}')
    for rule in app.url_map.iter_rules():
        if request_rule == rule:
            docjson['current_route'] = str(request.url_rule).split("<")[0]
            for r in rule.methods:
                docjson['methods'][r] = json.loads(
                    '{"parameters":[],"arguments":[]}')

    fields = []
    postjsondata = ""
    for line in docstring.splitlines():
        if line.lstrip()[0:2] == ";;":
            if line.lstrip().split(":", 1)[0] == ";;field":
                j = json.loads(line.split(":", 1)[1])
                # Due to documentation route will always have a 'GET' method.
                docjson['methods']['GET']['parameters'].append(j)
            if line.lstrip().split(":", 1)[0] == ";;argument":
                j = json.loads(line.split(":", 1)[1])
                docjson['methods']['GET']['arguments'].append(j)
            if line.lstrip().split(":", 1)[0] == ";;gettablefieldnames":
                j = json.loads(line.split(":", 1)[1])
                docjson['gettablefieldnames'] = j
            if line.lstrip().split(":", 1)[0] == ";;postjson":
                j = json.loads(line.split(":", 1)[1])
                postjsondata = json.dumps(j, indent=2)

    if document == "documentation.md":
        resp = make_response(render_template(document, docjson=docjson))
        resp.headers['Content-type'] = 'text/markdown; charset=UTF-8'
        return resp
    if document == "documentation.htm":
        return render_template(document, docjson=docjson, jsonexample=jsonexample, postjsondata=postjsondata)
    return render_template(document, docjson=docjson, jsonexample=jsonexample, postjsondata=postjsondata)

######################
#Routes and Handelers#
######################

# Re-Index from MySQL
@app.route("/admin/reindex/", methods=['GET'])
@login_required
def reindex_from_mysql():
    
    # retval = json.loads('{}')
    return reindex()

# Unit Tests Route
@app.route("/admin/tests/", methods=['GET'])
@login_required
def unit_tests():
    # solr_to_mysql()
    tests = json.loads('{}')
    return tests



def normalize_rating(id):
    resourceresult = resources.search("id:"+id, rows=1)
    thisresource=resourceresult.docs[0]
    feedbackresults=feedback.search("resourceid:"+id, rows=100000000)
    ratings=[]
    for result in feedbackresults:
        if 'rating' in result.keys():
            ratings.append(result["rating"])
    ratingsaverage=sum(ratings) / len(ratings)
    thisresource['rating']=ratingsaverage
    thisresourcefinal=strip_version(thisresource)
    resources.add([thisresourcefinal])
    resources.commit()

# Add feedback Feedback
'''{"feedback":'good stuff',
"rating":4.9,
"timestamp":,
"email":"me@mysite.com",
"resourceid":'35ab5641-2719-4faf-8b1e-2c4c57e15f5e'
}'''
@app.route("/api/feedback/", defaults={'document': None}, methods=['GET','POST'])
@app.route("/api/feedback/<document>", methods=['GET', 'POST'])
def addfeedback(document):
    """ 
    GET:
        Builds Solr searches and returns results for feedback.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Not yet implemented
    PUT
        Not yet implemented
    DELETE
        Not yet implemented
    ;;field:{"name":"resourceid","type":"","example":"IDPLACEHOLDER","description":"Generate feedback for a resource by its ID"}
    """
    #gen timestamp
    if request.method == 'GET':
        this_docstring = addfeedback.__doc__
        if document is not None:
            allowed_documents = ['documentation.html',
                                    'documentation.md', 'documentation.htm']
            if document not in allowed_documents:
                return render_template('bad_document.html', example="documentation.html"), 400
            else:
   
                result1 = resources.search("*:*", rows=1)
                id = result1.docs[0]["id"]
                this_docstring = this_docstring.replace('IDPLACEHOLDER', id)
                
                return generate_documentation(this_docstring, document, request, True)
        else:
            returnjson={'resourceid':"all",'feedback':[]}
            if request.args.get('resourceid'):
                returnjson['resourceid']=request.args.get('resourceid')
                feedbackresults=feedback.search("resourceid:"+request.args.get('resourceid'), rows=100000000)
            else:
                feedbackresults=feedback.search("*:*", rows=100000000)
            
            for fb in feedbackresults:
                fb.pop('email', None)
                returnjson["feedback"].append(fb)
            return(returnjson)
    if request.method == 'POST':
        if document=="add":
            insertobj={}
            insertobj['ip']=request.remote_addr
            now = datetime.now()
            insertobj['timestamp']=now.strftime("%Y-%m-%dT%H:%M:%SZ")
            rating=None
            if request.is_json:
                content = request.get_json()
                if 'resourceid' in content.keys():
                    if len(content['resourceid']) > 0:
                        
                        results = resources.search("id:"+content['resourceid'], rows=1)
                        #if id exists:
                        if len(results.docs)>0 or content['resourceid']=="0":
                            insertobj['resourceid']=content['resourceid']
                        else:
                            return{"status":"error","message":"resourceid must be resource UUID or 0 for sitewide feedback."},400
                        if 'rating' in content.keys():
                            if isinstance(content['rating'], float) or isinstance(content['rating'], int):
                                rating=content['rating']
                                insertobj['rating']=rating
                            else:
                                return{"status":"error","message":"expecting float for rating value"},400
                        if 'email' in content.keys():
                            insertobj['email']=content['email']
                        else:
                            if current_user.is_authenticated:
                                userid=current_user.id
                                emailresults = users.search("id:\""+userid+"\"", rows=1)
                                insertobj['email']=emailresults.docs[0]['email']
                        if 'feedback' in content.keys():
                            insertobj['feedback']=content['feedback']
                        newuuid=str(uuid.uuid4())
                        insertobj['id']=newuuid
                        try:
                            feedback.add([insertobj])
                            feedback.commit()
                            newfeedback=Feedback(id=newuuid,value=json.dumps(insertobj))
                            db.session.add(newfeedback)
                            try:
                                db.session.commit()
                            except Exception as err:
                                db.session.rollback()
                                db.session.flush()
                                return({"status":"error","message":"Database commit failed"})
                            if content['resourceid']!="0" and 'rating' in content.keys():
                                normalize_rating(content['resourceid'])
                            return{"status":"success","message":"feedback has been added"},200
                        except Exception as err:
                            return{"status":"error","message":str(err)},400



                else:
                    return{"status":"error","message":"POST must include a resource ID or 0 for sitewide feedback"},400
            else:
                return{"status":"error","message":"No json found"},400



# Resource RRS Feed

@app.route('/rss')
def rss():
    fg = FeedGenerator()
    fg.title('Feed title')
    fg.description('Feed description')
    fg.link(href=request.host_url)
    results=resources.search("status:True",sort="created desc",rows=10)
    for resource in results.docs: 
        fe = fg.add_entry()
        fe.title(resource['title'])
        fe.link(href=resource['url'])
        fe.description(resource['abstract_data'])
        fe.guid(resource['id'], permalink=False) # Or: UUID?
        if 'submitter_name' in resource:
            thisname=resource['submitter_name']
            thisemail=resource['submitter_email']
        else:
            thisemail='Unknown'
            thisname='Unknown'
        fe.author(name=thisname, email=thisemail)
        fe.pubDate(resource['created'])

    response = make_response(fg.rss_str(pretty=True))
    response.headers.set('Content-Type', 'application/rss+xml')

    return response

# Resource interaction
@app.route("/api/resource/", defaults={'document': None}, methods=['POST'])
@app.route("/api/resource/<document>", methods=['GET', 'POST'])
@login_required
def learning_resource_post(document):
    """ 
    GET:
        Builds Documentation

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Builds Solr searches and returns results for learning resources.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr 
    PUT
        Not yet implemented
    DELETE
        Not yet implemented



    ;;field:{"name":"template","type":"","example":"template","description":"Generate empty resource from schema"}
    ;;field:{"name":"id","type":"string","example":"IDPLACEHOLDER","description":"The ID of the learning resource."}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:"""

    if request.method == 'POST':

        if request.is_json:
            template = temlate_doc('learningresources')
            content = request.get_json()
            if 'id' not in content or content['id']=="": #treat as if it is a new document
                    return insert_new_resource(content)
            else: #treat as existing
                    return update_resource(content)
                    return "not yet implemented."
                

    if request.method == 'GET':
        if document is not None:
            allowed_documents = ['documentation.html',
                                 'documentation.md', 'documentation.htm']
            if document not in allowed_documents:
                return render_template('bad_document.html', example="documentation.html"), 400
            else:
                this_docstring = learning_resource_post.__doc__ + \
                    json.dumps(temlate_doc('learningresources'))
                result1 = resources.search("*:*", rows=1)
                id = result1.docs[0]["id"]
                this_docstring = this_docstring.replace('IDPLACEHOLDER', id)
                return generate_documentation(this_docstring, document, request, True)

    return "Documentation not implemented."


@app.route("/api/resource/", defaults={'document': None}, methods=['GET'])
def learning_resource(document):
    if request.method == "GET":
        if document is None:
            if request.args.get('id'):
                if current_user.is_authenticated:
                    if "admin" in current_user.groups:
                        searchstring = "*:*"
                    else:
                        searchstring = "status:true"
                else:
                    searchstring = "status:true"
                searchstring = append_searchstring(searchstring, request, "id")
                results = resources.search(searchstring, rows=1)
                template = temlate_doc('learningresources')
                if len(results.docs) > 0:
                    normalized_content = normalize_result(
                        results.docs[0], template)
                    return "test"#normalized_content
                else:
                    return "No results found"
            else:
                return render_template('resource.json')
    return "Documentation not implemented."


# Resource interaction
@app.route("/api/resources/", defaults={'document': None}, methods=['GET', 'POST'])
@app.route("/api/resources/<document>", methods=['GET', 'POST'])
def learning_resources(document):
    """ 
    GET:
        Builds Solr searches and returns results for learning resources.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Builds Solr searches and returns results for learning resources.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr 
    PUT
        Not yet implemented
    DELETE
        Not yet implemented



    ;;field:{"name":"title","type":"string","example":"DataONE","description":"The title of the learning resource."}
    ;;field:{"name":"url","type":"string","example":"dataoneorg.github.io","description":""}
    ;;field:{"name":"access_cost","type":"float","example":"1.0","description":""}
    ;;field:{"name":"submitter_name","type":"string","example":"\\\"Amber E Budden\\\"","description":""}
    ;;field:{"name":"submitter_email","type":"string","example":"example@example.com","description":""}
    ;;field:{"name":"authors.givenName","type":"string","example":"Robert","description":""}
    ;;field:{"name":"authors.familyName","type":"string","example":"Mayernik","description":""}
    ;;field:{"name":"contributors.givenName","type":"string","example":"Robert","description":""}
    ;;field:{"name":"contributors.familyName","type":"string","example":"HOEBELHEINRICH","description":""}
    ;;field:{"name":"author_org.name","type":"string","example":"DataONE","description":""}
    ;;field:{"name":"creator","type":"string","example":"Nhoebelheinrich","description":""}
    ;;field:{"name":"contact","type":"string","example":"\\\"Nancy J.  Hoebelheinrich\\\"","description":""}
    ;;field:{"name":"contact_org","type":"string","example":"NASA","description":""}
    ;;field:{"name":"abstract_data","type":"string","example":"researchers","description":""}
    ;;field:{"name":"abstract_format","type":"string","example":"filtered_html","description":""}
    ;;field:{"name":"subject","type":"string","example":"Aerospace","description":""}
    ;;field:{"name":"keywords","type":"string","example":"\\\"Data management\\\"","description":""}
    ;;field:{"name":"licence","type":"string","example":"\\\"Creative Commons\\\"","description":""}
    ;;field:{"name":"usage_info","type":"string","example":"USGS","description":""}
    ;;field:{"name":"citation","type":"string","example":"research","description":""}
    ;;field:{"name":"locator_data","type":"string","example":"\\\"10.5281/zenodo.239090\\\"","description":""}
    ;;field:{"name":"locator_type","type":"string","example":"DOI","description":""}
    ;;field:{"name":"publisher","type":"string","example":"\\\"Oak Ridge National Laboratory\\\"","description":""}
    ;;field:{"name":"version","type":"string","example":"\\\"1.0\\\"","description":""}
    ;;field:{"name":"access_features","type":"string","example":"Transformation","description":""}
    ;;field:{"name":"language_primary","type":"string","example":"es","description":""}
    ;;field:{"name":"languages_secondary","type":"string","example":"fr","description":""}
    ;;field:{"name":"ed_frameworks.name","type":"string","example":"\\\"FAIR Data Principles\\\"","description":""}
    ;;field:{"name":"ed_frameworks.nodes.name","type":"string","example":"Local Data Management","description":""}
    ;;field:{"name":"ed_frameworks.nodes.description","type":"string","example":"x","description":""}
    ;;field:{"name":"ed_frameworks.nodes.url","type":"string","example":"dataone.org","description":""}
    ;;field:{"name":"target_audience","type":"string","example":"\\\"Research scientist\\\"","description":""}
    ;;field:{"name":"purpose","type":"string","example":"\\\"Professional Development\\\"","description":""}
    ;;field:{"name":"completion_time","type":"string","example":"\\\"1 hour\\\"","description":""}
    ;;field:{"name":"media_type","type":"string","example":"\\\"Moving Image\\\"","description":""}
    ;;field:{"name":"lr_type","type":"string","example":"\\\"Learning Activity\\\"","description":""}
    ;;field:{"name":"limit","type":"int","example":"15","description":"Maximum number of results to return. Default is 10"}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:{"search": [{"group": "and","and": [{"field": "keywords","string": "ethics","type": "simple"},{"field": "created","string": "2019-05-20T17:33:18Z","type": "gte"} ],"or": [{"field": "submitter_name","string": "Karl","type": "simple"}]}],"limit": 10,"offset": 5, "sort":"id asc"}
    {"search":[{"group":"and","and":[{"string":"Data archiving","field":"keywords","type":"match"}]}]}
    """
    summary=False
    if document is None:
        document = 'search.json'
    allowed_documents = ['search.json', 'documentation.html',
                         'documentation.md', 'documentation.htm', 'search.jsonld']

    if document not in allowed_documents:
        return render_template('bad_document.html', example="search.json"), 400

    if request.method == 'GET':
        params = {
            'facet': 'on',
            'facet.field': resources_facets

        }
        if "search" not in document:
            return generate_documentation(learning_resources.__doc__, document, request, True)

        searchstring = "*:*"
        searchstring = append_searchstring(searchstring, request, "status")
        searchstring = append_searchstring(searchstring, request, "title")
        searchstring = append_searchstring(searchstring, request, "url")
        searchstring = append_searchstring(
            searchstring, request, "access_cost")
        searchstring = append_searchstring(
            searchstring, request, "submitter_name")
        searchstring = append_searchstring(
            searchstring, request, "submitter_email")
        searchstring = append_searchstring(searchstring, request, "author_names")
        searchstring = append_searchstring(searchstring, request, "authors.givenName")
        searchstring = append_searchstring(searchstring, request, "authors.familyName")
        searchstring = append_searchstring(searchstring, request, "authors.name_identifier")
        searchstring = append_searchstring(searchstring, request, "authors.name_identifier_type")
        searchstring = append_searchstring(searchstring, request, "contributors.givenName")
        searchstring = append_searchstring(searchstring, request, "contributors.familyName")
        searchstring = append_searchstring(searchstring, request, "ed_frameworks.nodes.name")
        searchstring = append_searchstring(searchstring, request, "ed_frameworks.nodes.description")
        searchstring = append_searchstring(searchstring, request, "ed_frameworks.nodes.url")
        searchstring = append_searchstring(searchstring, request, "creator")
        searchstring = append_searchstring(searchstring, request, "author_org.name")
        searchstring = append_searchstring(searchstring, request, "author_org.name_identifier")
        searchstring = append_searchstring(searchstring, request, "author_org.name_identifier_type")
        searchstring = append_searchstring(searchstring, request, "contact")
        searchstring = append_searchstring(
            searchstring, request, "contact_org")
        searchstring = append_searchstring(
            searchstring, request, "abstract_data")
        searchstring = append_searchstring(
            searchstring, request, "abstract_format")
        searchstring = append_searchstring(searchstring, request, "subject")
        searchstring = append_searchstring(searchstring, request, "keywords")
        searchstring = append_searchstring(searchstring, request, "licence")
        searchstring = append_searchstring(
            searchstring, request, "usage_info")
        searchstring = append_searchstring(searchstring, request, "citation")
        searchstring = append_searchstring(
            searchstring, request, "locator_data")
        searchstring = append_searchstring(
            searchstring, request, "locator_type")
        searchstring = append_searchstring(searchstring, request, "publisher")
        searchstring = append_searchstring(searchstring, request, "version")
        searchstring = append_searchstring(searchstring, request, "created")
        searchstring = append_searchstring(searchstring, request, "published")
        searchstring = append_searchstring(
            searchstring, request, "access_features")
        searchstring = append_searchstring(
            searchstring, request, "language_primary")
        searchstring = append_searchstring(
            searchstring, request, "languages_secondary")
        searchstring = append_searchstring(
            searchstring, request, "ed_framework")
        searchstring = append_searchstring(
            searchstring, request, "ed_framework_dataone")
        searchstring = append_searchstring(
            searchstring, request, "ed_framework_fair")
        searchstring = append_searchstring(
            searchstring, request, "target_audience")
        searchstring = append_searchstring(searchstring, request, "purpose")
        searchstring = append_searchstring(
            searchstring, request, "completion_time")
        searchstring = append_searchstring(searchstring, request, "media_type")
        searchstring = append_searchstring(searchstring, request, "lr_type")
        searchstring = append_searchstring(searchstring, request, "author")
        searchstring = append_searchstring(searchstring, request, "id")

        rows = 10
        if request.args.get("summary"):
            if request.args.get("summary").lower() in ['true', '1', 't', 'y', 'yes']:
                summary=True
        if request.args.get("limit"):
            if request.args.get("limit").isnumeric():
                rows = int(request.args.get("limit"))
        if request.args.get("offset"):
            if  request.args.get("offset").isnumeric():
                start = int(request.args.get("offset"))
            else:
                start = 0
        else:
            start = 0        
        results = resources.search(searchstring, **params, fl="*,score" ,rows=rows, start=start)
        newresults = resources.search(searchstring, fl="id",rows=rows, start=start)
        newarray=[]
        for newres in newresults:
            newarray.append(newres['id'])

        sqlresults=db.session.query(Learningresources).filter(Learningresources.id.in_(newarray)).all()   
        if document == "search.jsonld":
            return format_resource_jsonld_fromdb(results,sqlresults)
        if document == "search.json":
            if summary:
                return format_resource_fromdb_summary(results)
            else:
                return format_resource_fromdb(results,sqlresults)

    if request.method == 'POST':
        params = {
            'facet': 'on',
            'facet.field': resources_facets

        }
        operators = ['AND', 'NOT', 'OR']
        # searchstring = "status:true"
        searchstring = "*:*"
        if request.is_json:
            content = request.get_json()
            if len(content['search']) > 0:
                for index, group in enumerate(content['search']):
                    qindex = 0
                    if group['group'].upper() in operators:
                        searchstring += " "+group['group'].upper()+" ("
                        for num, key in enumerate(group.keys()):
                            if key.upper() in operators:
                                for q in group[key]:
                                    if q['type'] == 'simple':
                                        if qindex > 0:
                                            searchstring += " "+key.upper()+" "
                                        qindex += 1
                                        searchstring += q['field'] + \
                                            ":"+q['string']
                                    elif q['type'] == 'match':
                                        if qindex > 0:
                                            searchstring += " "+key.upper()+" "
                                        qindex += 1
                                        searchstring += q['field'] + \
                                            ":\""+q['string']+"\""
                                    elif q['type'] == 'startswith':
                                        if qindex > 0:
                                            searchstring += " "+key.upper()+" "
                                        qindex += 1
                                        searchstring += q['field'] + \
                                            ":"+q['string']+"*"
                                    elif q['type'] == 'lte':
                                        if qindex > 0:
                                            searchstring += " "+key.upper()+" "
                                        qindex += 1
                                        searchstring += q['field'] + \
                                            ":[* TO \""+q['string']+"\"]"
                                    elif q['type'] == 'gte':
                                        if qindex > 0:
                                            searchstring += " "+key.upper()+" "
                                        qindex += 1
                                        searchstring += q['field'] + \
                                            ":[ \""+q['string']+"\" TO *]"
                        searchstring += ")"


            # sort='id asc'
            searchstringexample=searchstring
            returntype="json"
            if 'format' in content.keys():
                returntype = content['format']
            else:
                returntype="json"
            if 'summary' in content.keys():
              
                summary = content['summary']
            else:
                summary = False
            if 'sort' in content.keys():
                sort = content['sort']
                searchstringexample=searchstringexample+", sort="+str(content['sort'])
            else:
                sort = ""

            if 'limit' in content.keys():
                rows = content['limit']
                searchstringexample=searchstringexample+", limit="+str(content['limit'])
            else:
                rows = 10

            if 'offset' in content.keys():
                start = content['offset']
                searchstringexample=searchstringexample+", offset="+str(content['offset'])
            else:
                start = 0
            if 'example' in content.keys():
                if content['example']==True:
                    return {"searchstring":searchstringexample}
            results = resources.search(searchstring, **params, fl="*,score" ,sort=sort,rows=rows, start=start)
            newresults = resources.search(searchstring, **params, fl="id",sort=sort,rows=rows, start=start)
            newarray=[]
            for newres in newresults:
                newarray.append(newres['id'])


            sqlresults=db.session.query(Learningresources).filter(Learningresources.id.in_(newarray)).all()   
            
            if returntype == "jsonld":
                return format_resource_jsonld_fromdb(results,sqlresults)
            else:
                if summary:
                    return format_resource_fromdb_summary(results)
                else:
                    return format_resource_fromdb(results,sqlresults)

        else:
            return 'json not found'
        return 'No query processed'
    if request.method == 'PUT':
        return "Method not yet implemented"
    if request.method == 'DELETE':
        return "Method not yet implemented"
    # default return for HEAD
    return "HEAD"


@app.route("/api/", methods=['GET'])
def api():
    """ 
    GET:
        Shows available routes with links to documentation built dynamically.


    Returns: 
            HTML

    """
    rulelist = []
    for rule in app.url_map.iter_rules():
        if "/api/" in rule.rule:
            if "<" not in rule.rule:
                if rule.rule != "/api/":
                    if rule.rule+"documentation.html" not in rulelist:
                        rulelist.append(rule.rule+"documentation.html")
    return render_template('api.html', rulelist=rulelist)


@app.route("/api/schema/", defaults={'collection': None, 'returntype': None}, methods=['GET'])
@app.route("/api/schema/<collection>.<returntype>", methods=['GET'])
# @login_required
def schema(collection, returntype):
    """ 
    GET:
        Builds Solr schema definition for a given collection from running config and returns selected return type.

        arguments: 

            collection (string):  An existing collection or 'documentation'
            returntype (string):  The mime type you want returned eg. html or pdf
        Returns: 
            returntype
    ;;argument:{"name":"documentation.html","description":"Show schema for the resources collection."}
    ;;argument:{"name":"documentation.md","description":"Show schema for the resources collection."}
    ;;argument:{"name":"resources.html","description":"Show schema for the resources collection."}
    ;;argument:{"name":"users.html","description":"Show schema for the users collection."}
    ;;argument:{"name":"vocabularies.html","description":"Show schema for the vocabularies collection."}
    ;;argument:{"name":"resources.md","description":"Return schema for the resources collection as Markdown"}
    ;;argument:{"name":"users.md","description":"Return schema for the users collection as Markdown."}
    ;;argument:{"name":"vocabularies.md","description":"Return schema for the vocabularies collection as Markdown."}
    ;;argument:{"name":"resources.pdf","description":"Return schema for the resources collection as PDF."}
    ;;argument:{"name":"users.pdf","description":"Return schema for the users collection as PDF."}
    ;;argument:{"name":"vocabularies.pdf","description":"Return schema for the vocabularies collection as PDF."}

    """

    allowed_collections = ['documentation', "resources",
                           "learningresources", "vocabularies", "taxonomies", "user", "users"]
    allowed_types = ['html']

    if collection not in allowed_collections or collection is None:
        return render_template('bad_document.html', example="api/schema/documentation.html"), 400

    if collection == "documentation":
        return generate_documentation(schema.__doc__, collection+"."+returntype, request)

    today = date.today().strftime("%d/%m/%Y")
    typemap = {"text_general": "General Text", "boolean": "Boolean",
               "pdate": "Datetime", "string": "Exact Match String", "pfloat": "Floating Point","booleans":"Boolean"}
    collectionmap = {"resources": "learningresources", "learningresources": "learningresources",
                     "vocabularies": "taxonomies", "taxonomies": "taxonomies", "user": "users", "users": "users"}
    r = requests.get(app.config["SOLR_ADDRESS"] +
                     collectionmap[collection]+"/schema/fields")
    schemajson = json.loads(
        '{"description":"Learning Resources Schema", "fields":[]}')
    if r.json():
        for field in r.json()['fields']:
            if not field['name'].startswith(('_', 'facet_')):
                thisfield = json.loads("{}")
                thisfield['name'] = field['name']
                thisfield['type'] = typemap[field['type']]
                schemajson['fields'].append(thisfield)
                if 'multivalue' in field:
                    thisfield['multivalue'] = field['multiValued']
                if 'required' in field:
                    thisfield['required'] = field['required']
        if returntype == "json":
            return(schemajson)
        if returntype == "md":
            resp = make_response(render_template(
                "schema.md", schemajson=schemajson, collection=collection))
            resp.headers['Content-type'] = 'text/markdown; charset=UTF-8'
            return resp
            # return render_template("schema.md", schemajson=schemajson, collection=collection)
        if returntype == "html":
            return render_template("schema.html", schemajson=schemajson, collection=collection, html=True, date=today)
        if returntype == "pdf":
            schemapdfhtml = HTML(string=render_template(
                "schema.html", schemajson=schemajson, collection=collection, date=today))
            resp = make_response(schemapdfhtml.write_pdf())
            resp.headers['Content-type'] = 'application/pdf'
            return resp
    return(schemajson)


def add_timestamp(id,timestamp_type,current_user,request):


    if current_user.is_authenticated:
        userid=current_user.id
    else:
        userid=None
    now = datetime.now()
    nowstr=now.strftime("%Y-%m-%dT%H:%M:%SZ")
    #If id does not create it with new timestamp_type entry
    timestamp_json = json.loads('{ "resourceid":"'+id+'"}')
    timestamp_json['timestamp']=nowstr
    timestamp_json['userid']=userid
    timestamp_json['type']=timestamp_type
    timestamp_json['ip']=request.remote_addr
    timestamps.add([timestamp_json])
    timestamps.commit()

#TODO MYSQL?????




def check_urls():
    resourcelist = resources.search("*:*", fl="id,url", rows=100000)
    for resource in resourcelist:
        try:
            r = requests.head(resource["url"],allow_redirects=True)
            if r.status_code == 200:
                pass
            else:
                print(resource["url"])
                print(r.status_code)
        except:
            print("Error") 
            print(resource["url"]) 

@app.route("/admin/urlcheck/",  methods=['GET'])
def urlcheck():
   
    if current_user.is_authenticated:
        if "admin" in current_user.groups:
            linkcheck = threading.Thread(target=check_urls)
            linkcheck.start()
            return("You are admin")

        else:
            return("You must be admin")
    else:
        return("You must be a logged in as admin to start a check.")
   
@app.route("/api/access/<id>", methods=['GET'])
def access(id):
    """ 
    GET:
        Logs resource access.
        
        Parameters: 

            id :  The ID of the resource being accessed.

        Returns: 
            respones:HTTPD STATUS
    POST:
        Not  implemented
    PUT
        Not  implemented
    DELETE
        Not  implemented

    """

    idresults = resources.search("id:"+id)
    #If the id exists as a resource...
    if len(idresults.docs)>0:
        add_timestamp(id,"access",current_user,request)
        return redirect(idresults.docs[0]["url"], code=302)
    # else return id not found.. 
    else:
        return("ID not found")
    return ''
    
@app.route("/api/vocabularies/", defaults={'document': None}, methods=['GET','POST'])
@app.route("/api/vocabularies/<document>", methods=['GET'])
def vocabularies(document):
    """ 
    GET:
        Builds Solr searches and returns results for learning resources.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Not yet implemented
    PUT
        Not yet implemented
    DELETE
        Not yet implemented
;;field:{"name":"name","type":"string","example":"\\\"Organizations\\\"","description":"Name of vocabulary"}
    ;;field:{"name":"id","type":"UUID","example":"IDPLACEHOLDER","description":"ID of vocabulary"}
    
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    """

    if document == "edit":
        if current_user.is_authenticated:
            if "admin" in current_user.groups:
                return render_template("edit_vocab.html")
            else:
                return{"status":"error","message":"Only admins can edit vocabularies."},400
        else:
            return{"status":"error","message":"Only admins can edit vocabularies."},400

    if document == "add":
        if current_user.is_authenticated:
            if "admin" in current_user.groups:
                return render_template("add_vocab.html")
            else:
                return{"status":"error","message":"Only admins can add vocabularies."},400
        else:
            return{"status":"error","message":"Only admins can add vocabularies."},400

    if document is None:
        document = 'search.json'
    allowed_documents = ['search.json', 'documentation.html',
                         'documentation.md', 'documentation.htm']

    if document not in allowed_documents:
        return render_template('bad_document.html', example="search.json"), 400

    if request.method == 'GET':
        if document != "search.json":
            result1 = taxonomies.search("*:*", rows=1)
            id = result1.docs[0]["id"]
            this_docstring = vocabularies.__doc__
            this_docstring = this_docstring.replace('IDPLACEHOLDER', id)
            return generate_documentation(this_docstring, document, request, True)
        searchstring = "*:*"
        returnval = json.loads(
            '{ "documentation":"'+request.host_url+'api/vocabularies/documentation.html","names":[]}')
        if len(request.args) > 0:
            if request.args.get("names") == "true":

                results = taxonomies.search("*:*")
                for result in results:
                    returnval["names"].append(result["name"])
                return returnval
            else:
                searchstring = append_searchstring(
                    searchstring, request, "name")
                searchstring = append_searchstring(
                    searchstring, request, "values")
                searchstring = append_searchstring(searchstring, request, "id")
                returnval = json.loads(
                    '{ "documentation":"API documentation string will go here","results":[]}')
                results = taxonomies.search(searchstring,rows=1000000)
                for result in results:
                    result.pop('_version_', None)
                    returnval["results"].append(result)
                returnval['hits'] = results.hits
                returnval['hits-returned'] = len(results)
                return returnval
                
        else:
            returnval = json.loads(
                '{ "documentation":"'+request.host_url+'api/vocabularies/documentation.html","results":[]}')
            results = taxonomies.search("*:*",rows=100000)
            for result in results:
                result.pop('_version_', None)
                returnval["results"].append(result)
            returnval["results"]=sorted(returnval["results"], key=lambda k: k['name'].lower())
            returnval['hits'] = results.hits
            returnval['hits-returned'] = len(results)
            return returnval
    if request.method == 'POST':
        if current_user.is_authenticated:
            if "admin" in current_user.groups:
                if request.is_json:
                    vocabjson  = request.get_json()
                    #check if it has id,name, and values
                    if all(key in vocabjson for key in ("name","values", "id")):
                        if vocabjson['id'] and vocabjson['name'] and vocabjson['values']:
                            #clean it up:
                            newvocabjson={'id':vocabjson['id'],'name':vocabjson['name'],'values':vocabjson['values']}
                            taxonomies.add([newvocabjson])
                            taxonomies.commit()
                            db.session.query(Taxonomies).filter(Taxonomies.id == newvocabjson['id']).update({Taxonomies.value:json.dumps(newvocabjson)}, synchronize_session = False)
                            try:
                                db.session.commit()
                            except Exception as err:
                                print(err)
                                db.session.rollback()
                                db.session.flush()
                                return({"status":"error","message":"Database commit failed"})
                            return{"status":"success","message":"json rec"},200
                    elif all(key in vocabjson for key in ("name","values")):
                        if vocabjson['name'] and vocabjson['values']:
                            taxresults = taxonomies.search("name:\""+vocabjson['name']+"\"",rows=1)
                            if len(taxresults.docs)==0:
                                newuuid=str(uuid.uuid4())
                                newvocabjson={'id':newuuid,'name':vocabjson['name'],'values':vocabjson['values']}
                                taxonomies.add([newvocabjson])
                                taxonomies.commit()
                                
                                newtax=Taxonomies(id=newuuid,value=json.dumps(newvocabjson))
                                db.session.add(newtax)
                                try:
                                    db.session.commit()
                                except Exception as err:
                                    print(err)
                                    db.session.rollback()
                                    db.session.flush()
                                    return({"status":"error","message":"Database commit failed"})
                                return{"status":"success","message":"Vocabulary has been added."},200
                            else:
                                return{"status":"error","message":"Vocabulary with that title already exists."},400
                        else:
                            return{"status":"error","message":"json rec must have id, name and values keys"},400
                else:
                    return{"status":"error","message":"Vocabularies JSON expected."},400
            else:
                return{"status":"error","message":"Only admins can modify vocabularies."},400
        else:
            return{"status":"error","message":"You must be logged in"},400



@app.route("/login/", methods=['GET','POST'])
def login():
    """ 
    GET:

        Returns: 
            HTML login form.
    POST:
        Validates credentials of users and creates and stores a session.
        Form Request: 

            username (string):  The users username.
            password (string):  The users password.
        Returns: 
            cookie:session token
    """
    if request.method == 'GET':
        return render_template("login.html")
    if request.method == 'POST':
        user_object = get_user(request.form['username'])
        if user_object:
            computed = user_object['hash']
            passwd = request.form['password']
            if drash.verify(passwd, computed):
                login_user(
                    User(user_object['id'], user_object['groups'], user_object['name']))
                return redirect(url_for('protected'))

        return 'Bad login'


@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/protected')
@login_required
def protected():
    return 'Logged in as: ' + current_user.name 


@app.route("/")
def hello():
    return render_template("index.html")
    return "DMT Clearinghouse."

@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)

@app.route('/css/<path:path>')
def send_js(path):
    return send_from_directory('css', path)

@app.route('/img/<path:path>')
def send_js(path):
    return send_from_directory('img', path)

def validate_groups(grouparray):
    valid=True
    for group in grouparray:
        if group not in ["admin","editor","reviewer","submitter"]:
            valid=False
    return(valid)


def validate_timezone(tz):
    timezones_search=taxonomies.search("name:timezones")
    timezones =timezones_search.docs[0]
    if tz in timezones['values']:
        return True
    return False

def new_token(uuid):
    token_string=randomString(40)
    newtoken=Tokens(token=token_string,date=datetime.now(),uuid=uuid) 
    db.session.add(newtoken)
    try:
        db.session.commit()
        return token_string
    except Exception as err:
        db.session.rollback()
        db.session.flush()
        return({"status":"error","message":"Database commit failed"})
    # return token_string

def send_mail(message,subject,isfrom,isto):
    try:
        msg = EmailMessage()
        msg.set_content(message)

        msg['Subject'] = subject
        msg['From'] = isfrom
        msg['To'] = isto

        s = smtplib.SMTP('localhost')
        s.send_message(msg)
        s.quit()
        return True
    except:
        return False


@app.route("/passwordreset/", methods=['GET','POST'])
def passwordreset():
    yesterday=datetime.now() - timedelta(days=1)
    if request.method == 'GET':
        
        if request.args.get('token'):
            token = request.args.get('token')
            tokentuple=db.session.query(Tokens.token).filter(Tokens.token == token).filter(Tokens.date>=yesterday).first()
            if tokentuple:
                return render_template("password_reset.html",token=token,url=request.host_url+"passwordreset/")
            return {"status":"error","message":"token not found."}
        else: 
            return({"status":"error","message":"no token in arguments list"})
    if request.method == 'POST':
        usercontent = request.get_json()
        if usercontent['token'] and usercontent['pass']:
            tokentuple=db.session.query(Tokens.uuid).filter(Tokens.token == usercontent['token']).filter(Tokens.date>=yesterday).first()
            if tokentuple: #change the password and remove token then respond with gr86S
                this_user=users.search("id:\""+tokentuple[0]+"\"", rows=1)
                if len(this_user.docs)!=0:
                    hashpw=drash.encode(usercontent['pass'])
                    userjson=this_user.docs[0]
                    userjson.pop('_version_', None)
                    userjson['hash']=hashpw

                    users.add([userjson])
                    users.commit()
                    #remove token from mysql
                    tokens_to_delete=db.session.query(Tokens).filter(Tokens.token == usercontent['token']).all()
                    for ttd in tokens_to_delete:
                        session.delete(ttd)
                        try:
                            db.session.commit()
                        except Exception as err:
                            db.session.rollback()
                            db.session.flush()
                            return({"status":"error","message":"Database commit failed"})
                    return({"status":"success","message":"password updated"})
                else:
                    return({"status":"error","message":"token not found or expired."})
            return({"status":"error","message":"token not found or expired."})
        else:
            return({"status":"error","message":"keys token and pass are required."})

        return":)"



@app.route("/user/groups", methods=['GET'])
def user_groups():
    if current_user.is_authenticated:
        jsonobj={'groups':current_user.groups}
    else:
        jsonobj={'groups':[]}
    return json.dumps(jsonobj)


@app.route("/user/<action>", methods=['GET','POST'])
def user(action):
    if request.method == 'GET':
        if action=="pwreset":
                return render_template("password_reset_request.html")
        if action=="create":
                return render_template("adduser_public.html")
        if current_user.is_authenticated:
            if "admin" in current_user.groups:
                userjson=[]
                results = users.search("*:*",rows=1000000)
                groups=[]
                for user in results:
                    user.pop('_version_', None)
                    user.pop('hash', None)
                    for group in user['groups']:
                        if group not in groups:
                            if group !="oauth":
                                groups.append(group)
                    userjson.append(user)
                if action=="add":
                    return render_template("adduser.html",groups=groups)
                if action=="edit":

                    sorteduserjson = sorted(userjson, key=lambda k: k['name'].lower())     
                    return render_template("edit.html", userjson=sorteduserjson,groups=groups)
 
            else:
                return{"status":"error","message":"Only admins can add users."},400
        else:
            return{"status":"error","message":"You must be logged in to add users."},400
                
    if request.method == 'POST':
        returnjson={"status":"success"}
        usercontent=None
        if request.is_json:
            usercontent = request.get_json()
        else:
            return({"status":"error","message":"no JSON found in post"})
        if usercontent:
            if action=="search":
                if current_user.is_authenticated: #TODO ADMIN
                    if "admin" in current_user.groups:
                        if "search" in usercontent:
                            userjson=[]
                            these_users=users.search("name:"+usercontent['search']+"* OR email:"+usercontent['search']+"*", rows=100000)
                            for user in these_users:
                                user.pop('_version_', None)
                                user.pop('hash', None)
                                userjson.append(user)
                            sortedusers=sorted(userjson, key=lambda k: k['name'].lower()) 
                            returnvalue={"status":"success","users":sortedusers}
                            return returnvalue
                        return{"status":"error","message":"search not found in json"},400
                    return{"status":"error","message":"You must be admin to search for users"},400
                return{"status":"error","message":"You must be authenticated to search for users"},400
            if action=="create":
                if all (key in usercontent for key in ("name","email")):
                    if len(usercontent['name'])>0 and len(usercontent['email'])>0:
                        emailresults = users.search("email:\""+usercontent['email']+"\"", rows=1)
                        if len(emailresults.docs)==0:
                            results = users.search("name:\""+usercontent['name']+"\"", rows=1)
                            if len(results.docs)==0:
                                hashpw=None
                                groups=None
                                enabled=True
                                if usercontent['timezone']:
                                    timezone=usercontent['timezone']
                                else:
                                    timezone=""
                                hashpw=drash.encode(randomString(20))
                                groups=["submitter","lauth"]
                                email=usercontent['email']
                                name=usercontent['name']
                                newuuid=str(uuid.uuid4())
                                userjson={
                                        "hash":hashpw,
                                        "name":name,
                                        "email":email,
                                        "timezone":timezone,
                                        "groups":groups,
                                        "enabled":enabled,
                                        "id":newuuid
                                        }
                                users.add([userjson])
                                users.commit()
                                token=new_token(newuuid)
                                resetlink=request.host_url+"/passwordreset/?token="+token
                                servername=request.host_url
                                emailbody=render_template("adduser_email.html",username=name, resetlink=resetlink,servername=servername)
                                subject="Your new account for " + request.host_url
                                isfrom='noreply@'+request.host_url
                                if send_mail(emailbody,subject,isfrom,email):
                                    newuser=Users(id=newuuid,value=json.dumps(userjson)) 
                                    db.session.add(newuser)
                                    try:
                                        db.session.commit()
                                    except Exception as err:
                                        db.session.rollback()
                                        db.session.flush()
                                        return({"status":"error","message":"Database commit failed"})
                                    return {"status":"success","message":"User account created."},200
                                else:
                                    return{"status":"error","message":"Could not send email to "+usercontent['email']+"."},400
    
                            else:
                                return {"status":"error","message":"User "+usercontent['name']+" already exists. If this is your username, please reset your password."},400
                        else:
                            return{"status":"error","message":"user with email "+usercontent['email']+" already exists. Redirecting to password reset page"},409
                    else:
                        return{"status":"error","message":"To create a user both name and email need to be provided."},400
                else:
                    return{"status":"error","message":"To create a user both name and email keys need to be in json provided."},400

            if action=="add":
                if current_user.is_authenticated:
                    if "admin" in current_user.groups:
                        if all (key in usercontent for key in ("name","email")):
                            if len(usercontent['name'])>0 and len(usercontent['email'])>0:

                                results = users.search("name:\""+usercontent['name']+"\"", rows=1)
                                if len(results.docs)==0:
                                    emailresults = users.search("email:\""+usercontent['email']+"\"", rows=1)
                                    if len(emailresults.docs)==0:
                                        hashpw=None
                                        groups=None
                                        enabled=True
                                        if usercontent['timezone']:
                                            timezone=usercontent['timezone']
                                        else:
                                            timezone=""
                                        if "password" in usercontent:
                                            hashpw=drash.encode(usercontent["password"])
                                        else:
                                            hashpw=drash.encode(randomString(20))
                                        if "groups" in usercontent:
                                            if validate_groups(usercontent["groups"]):
                                                groups=usercontent["groups"]
                                            else:
                                                groups=["submitter","lauth"]
                                        else:
                                            groups=["submitter"]
                                        if "enabled" in usercontent:
                                            enabled=usercontent["enabled"]
                                        email=usercontent['email']
                                        name=usercontent['name']
                                        newuuid=str(uuid.uuid4())
                                        userjson={
                                                "hash":hashpw,
                                                "name":name,
                                                "email":email,
                                                "timezone":timezone,
                                                "groups":groups,
                                                "enabled":enabled,
                                                "id":newuuid
                                                }
                                        users.add([userjson])
                                        users.commit()


                                        token=new_token(newuuid)
                                        resetlink=request.host_url+"/passwordreset/?token="+token
                                        servername=request.host_url
                                        emailbody=render_template("adduser_email.html",username=name, resetlink=resetlink,servername=servername)
                                        subject="Your new account for " + request.host_url
                                        isfrom='noreply@'+request.host_url
                                        if send_mail(emailbody,subject,isfrom,email):
                                            newuser=Users(id=newuuid,value=json.dumps(userjson)) 
                                            db.session.add(newuser)
                                            try:
                                                db.session.commit()
                                            except Exception as err:
                                                db.session.rollback()
                                                db.session.flush()
                                                return({"status":"error","message":"Database commit failed"})
                                            return {"status":"success","message":"User account created."},200
                                        else:
                                            return{"status":"error","message":"Could not send email to "+usercontent['email']+"."},400
            
                                    else:
                                        return{"status":"error","message":"user with email "+usercontent['email']+" already exists. No action taken."},400
                                else:
                                    return {"status":"error","message":"User "+usercontent['name']+" already exists. No action taken."},400
                            else:
                                return{"status":"error","message":"To create a user both name and email need to be provided."},400
                        else:
                            return{"status":"error","message":"To create a user both name and email keys need to be in json provided."},400
                    else:
                        return{"status":"error","message":"Only admins can add users."},400
                else:
                    return{"status":"error","message":"You must be logged in to add users."},400
            if action=="edit":
                if current_user.is_authenticated:
                    if "admin" in current_user.groups:
                        if usercontent['id']:
                            account = users.search("id:\""+usercontent['id']+"\"", rows=1)
                            if len(account.docs)!=0:
                                
                                accountinfo=account.docs[0]
                                accountinfo.pop('_version_', None)
                                if usercontent['name']:
                                    accountinfo['name']=usercontent['name']
                                if usercontent['email']:
                                    accountinfo['email']=usercontent['email']
                                if usercontent['timezone']:
                                    accountinfo['timezone']=usercontent['timezone']
                                if usercontent['groups']:
                                    accountinfo['groups']=usercontent['groups']
                                if usercontent['enabled']:
                                    accountinfo['enabled']=usercontent['enabled']
                                out=users.add([accountinfo])
                                users.commit()
                                Users(id=usercontent['id'],value=json.dumps(accountinfo)) 
                                return{"status":"success","message":"Account info for "+usercontent['name']+" has been updated"},200
                              

                            else:
                                return{"status":"error","message":"UUID for user not found."},400
                        else:
                            return{"status":"error","message":"No account ID in json post"},400   
                    else:
                        return{"status":"error","message":"Only admins can add users."},400
                else:
                    return{"status":"error","message":"You must be logged in to add users."},400
            if action=="pwreset":
                if 'email' in usercontent:
                    if usercontent['email']:
                        emailresults = users.search("email:\""+usercontent['email']+"\"", rows=1)
                    
                        
                        if len(emailresults.docs)!=0:
                            if len(usercontent['email'])>0:
                                token=new_token(emailresults.docs[0]['id'])
                                resetlink=request.host_url+"/passwordreset/?token="+token
                                servername=request.host_url
                                emailbody=render_template("password_reset_email.html", resetlink=resetlink,servername=servername)
                                subject="Password reset for " + request.host_url
                                isfrom='noreply@'+request.host_url
                                if send_mail(emailbody,subject,isfrom,usercontent['email']):
                                    return({"status":"success","message":"password reset link sent."})
                                else:
                                    return{"status":"error","message":"could not send mail"},500
                            else:
                                return{"status":"error","message":"required elements cannot be empty strings."},400
                        else:
                            return{"status":"error","message":"email does not exist in api."},400
                    else:
                        return{"status":"error","message":"email key is requried in json POST"},400
                else:
                    return{"status":"error","message":"email not found in post json"},400
            return({"status":"error","message":"Method "+action+" not found"})
        else:
            return({"status":"error","message":"no JSON found in post"})
    return("How did I get here.")
@app.route("/static/<path:path>")
def send_static(path):
    return send_from_file('static', path)


orcid_client_id = app.config["ORCID_CLIENT_ID"]
orcid_client_secret = app.config["ORCID_CLIENT_SECRET"]
orcid_discovery_url = app.config["ORCID_AUTH_URL"]
orcid_exchange_url = app.config["ORCID_EXCHANGE_URL"]
orcid_redirect_url = app.config["ORCID_REDIRECT_URL"]

orcid_client = WebApplicationClient(orcid_client_id)

@app.route("/orcid_sign_in", methods = ["GET", "POST"])
def orcid_sign_in():
    request_uri = orcid_client.prepare_request_uri(
        orcid_discovery_url,
        redirect_uri= orcid_redirect_url,
        scope="openid",  #use "openid" or "/authenticate"
    )
    return redirect(request_uri)

@app.route("/orcid_sign_in/orcid_callback", methods = ["GET", "POST"])
def orcid_callback():
    
    code = request.args.get("code")
    token_endpoint = orcid_exchange_url
    # TODO look at documentation for prepare_token_request() and see how a request is made at 
    # https://members.orcid.org/api/oauth/3legged-oauth
    token_url, headers, body = orcid_client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
        client_secret = orcid_client_secret
    )

    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(orcid_client_id, orcid_client_secret),
    )
    orcid_client.parse_request_body_response(json.dumps(token_response.json()))
    orcid_id = token_response.json()['orcid']
    userinfo_endpoint = 'https://pub.orcid.org/v2.1/' + orcid_id +'/record'
    uri, headers, body = orcid_client.add_token(userinfo_endpoint) 
    headers["Content-Type"] = "application/json"
    userinfo_response = requests.get(uri, headers=headers, data=body)
    userinfo  = userinfo_response.json()
    email=""
    # if there are no emails available
    if userinfo.get("person").get('emails').get("email") == []:
        users_username = orcid_id #then username is the orcid ID
    else: #TODO we should loop through these and use the email listed as primary.
        email_address_list=userinfo["person"]["emails"]["email"]
        primary_email=""
        for ea in email_address_list: #loop through each email and search SOLR for it.
            emailsearchstr="email:\""+ea["email"]+"\""
            eaobj=users.search(emailsearchstr, rows=1)
            if len(eaobj.docs)>0: #If we find one, use it as the account to login.
                userid=eaobj.docs[0]["id"]
                if 'oauth' not in eaobj.docs[0]["groups"]: #If oauth is not in groups add it and update records.
                    eaobj.docs[0]["groups"].append('oauth')
                    db.session.query(Users).filter(Users.id == userid).update({Users.value:json.dumps(eaobj.docs[0])}, synchronize_session = False) #update the record.
                    try:
                        db.session.commit()
                    except Exception as err:
                        db.session.rollback()
                        db.session.flush()
                        return({"status":"error","message":"Database commit failed"})
                    doc=strip_version(eaobj.docs[0])
                   
                    users.add([doc])
                    users.commit()
                    #otherwise just log them in.
                login_user(User(eaobj.docs[0]['id'], eaobj.docs[0]['groups'], eaobj.docs[0]['name']))
                return redirect(url_for('protected'))
            if ea['primary']:
                primary_email=ea["email"]



        #If we get here it is because no emails were found that match in the system.
        #so we use primary e-mail for both username and email address.
        users_username = primary_email
        email=primary_email
    #we could probably remove this check.
    userobj = users.search("name:\""+users_username+"\"", rows=1)
    newuuid=str(uuid.uuid4())
    #if email not found, create it and log in the user.
    if len(userobj.docs)==0:           
        hashpw=drash.encode(randomString())
        userjson={
        "hash":hashpw,
        "name":users_username,
        "email":email,
        "groups":["submitter","oauth"],
        "enabled":True,
        "id":newuuid
        }
        out=users.add([userjson])
        test = users.commit()
        newuser=Users(id=newuuid,value=json.dumps(userjson)) 
        
        db.session.add(newuser)
        try:
            db.session.commit()
        except Exception as err:
            db.session.rollback()
            db.session.flush()
            return({"status":"error","message":"Database commit failed"})
        login_user(User(newuuid, ["submitter","oauth"], users_username))
        return redirect(url_for('protected'))
    #Otherwise just log in the user.
    else:
        if userobj.docs[0]['enabled']:
            login_user(User(userobj.docs[0]['id'], userobj.docs[0]['groups'], userobj.docs[0]['name']))
            return redirect(url_for('protected'))
        else:
            return "User "+userobj.docs[0]['name']+" has been disabled by admin."
    
    return ":)" #redirect('/protected')

if __name__ == "__main__":
    app.run()
