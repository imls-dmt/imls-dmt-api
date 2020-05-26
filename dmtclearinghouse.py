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
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Date, Boolean, JSON
from sqlalchemy.orm import sessionmaker
import uuid
import threading
import time
import random
import string
import smtplib
from email.message import EmailMessage

# Create flask app
app = Flask(__name__)

def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

# Pull config info from file
app.config.from_object('dmtconfig.DevConfig')
engine = create_engine(app.config["CONNECT_STRING"])
meta = MetaData()
Base = automap_base()
Base.prepare(engine, reflect=True)
Learningresources = Base.classes.learningresources
Users =Base.classes.users
Taxonomies = Base.classes.taxonomies

resources_facets = ["facet_author_org", "facet_subject", "facet_keywords", "facet_license", "facet_usage_info", "facet_publisher", "facet_access_features",
                    "facet_language_primary", "facet_languages_secondary", "facet_ed_frameworks", "facet_target_audience", "facet_lr_type", "facet_purpose", "facet_media_type"]
# Create a pysolr object for accessing the "learningresources" and "users" index
resources = pysolr.Solr(
    app.config["SOLR_ADDRESS"]+"learningresources/", timeout=10)
users = pysolr.Solr(app.config["SOLR_ADDRESS"]+"users/", timeout=10)
taxonomies = pysolr.Solr(app.config["SOLR_ADDRESS"]+"taxonomies/", timeout=10)
timestamps = pysolr.Solr(app.config["SOLR_ADDRESS"]+"timestamps/", timeout=10)
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
    session = Session(engine)
    Learning_Resources_IDs_count=session.query(Learningresources).count()
    rescount=resources.search("*:*",rows=0)
    if rescount.raw_response['response']['numFound']==Learning_Resources_IDs_count:
        resources.delete(q='*:*')
        test = resources.commit()
        Learning_Resources_IDs_res=session.query(Learningresources).all()
        Learning_Resources_JSON=[]
        for doc in Learning_Resources_IDs_res:
            Learning_Resources_JSON.append(json.loads(doc.value))
            lrcount=lrcount+1
        resources.add(Learning_Resources_JSON)
        test = resources.commit()
        res=resources.search("*:*",rows=0)
        if res.raw_response['response']['numFound']==lrcount:
            returnj['result']['learning_resources']={"sucess":True,"count":lrcount}
        else:
            returnj['result']['learning_resources']={"sucess":False,"solrcount":res.raw_response['response']['numFound'],"sqlcount":lrcount}
    else:
        returnj['result']['learning_resources']={"sucess":False,"solrcount":rescount.raw_response['response']['numFound'],"sqlcount":Learning_Resources_IDs_count}
    
    lrcount=0
    Users_IDs_count=session.query(Users).count()
    rescount=users.search("*:*",rows=0)
    if rescount.raw_response['response']['numFound']==Users_IDs_count: 
        users.delete(q='*:*')
        test = users.commit()
        Users_IDs_res=session.query(Users).all()
        Users_IDs_JSON=[]
        for doc in Users_IDs_res:
            Users_IDs_JSON.append(json.loads(doc.value))
            lrcount=lrcount+1
        users.add(Users_IDs_JSON)
        test = users.commit()
        res=users.search("*:*",rows=0)
        if res.raw_response['response']['numFound']==lrcount:
            returnj['result']['users']={"sucess":True,"count":lrcount}
        else:
            returnj['result']['users']={"sucess":False,"solrcount":res.raw_response['response']['numFound'],"sqlcount":lrcount}
    else:
        returnj['result']['learning_resources']={"sucess":False,"solrcount":rescount.raw_response['response']['numFound'],"sqlcount":Users_IDs_count}


    lrcount=0
    Taxonomies_IDs_count=session.query(Taxonomies).count()
    rescount=taxonomies.search("*:*",rows=0)
    if rescount.raw_response['response']['numFound']==Taxonomies_IDs_count: 
        taxonomies.delete(q='*:*')
        test = taxonomies.commit()
        Taxonomies_IDs_res=session.query(Taxonomies).all()
        Taxonomies_IDs_JSON=[]
        for doc in Taxonomies_IDs_res:
            Taxonomies_IDs_JSON.append(json.loads(doc.value))
            lrcount=lrcount+1
        taxonomies.add(Taxonomies_IDs_JSON)
        test = taxonomies.commit()
        res=taxonomies.search("*:*",rows=0)
        if res.raw_response['response']['numFound']==lrcount:
            returnj['result']['taxonomies']={"sucess":True,"count":lrcount}
        else:
            returnj['result']['taxonomies']={"sucess":False,"solrcount":res.raw_response['response']['numFound'],"sqlcount":lrcount}
    else:
        returnj['result']['learning_resources']={"sucess":False,"solrcount":rescount.raw_response['response']['numFound'],"sqlcount":Taxonomies_IDs_count}



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
    j['id']=str(uuid.uuid4())
    session = Session(engine)
    session.add(Learningresources(id = j['id'], value=json.dumps(j)))
    try:
        session.commit()
    except Exception as err:
        db_session.rollback()
        db_session.flush()
        return({"status":"fail","error":str(err)})
    try:
        resources.add([j])
        test = resources.commit()
    except Exception as solrerr:
        db_session.rollback()
        db_session.flush()
        return({"status":"fail","error":str(solrerr)})
    return({"status":"success","error":None})

def update_resource(j):
    session = Session(engine)
    session.query(Learningresources).filter(Learningresources.id == j['id']).update({Learningresources.value:json.dumps(j)}, synchronize_session = False)
    
    try:
        session.commit()
        resources.add([j])
    except Exception as err:
        db_session.rollback()
        db_session.flush()
        return({"status":"fail","error":str(err)})

    return({"status":"success","error":None})

def get_score(results,uuid):
    score=None
    for res in results:
        if res['id']==uuid:
            score=res['score']
    return score

def format_resource_jsonld_fromdb(results,sqlresults):
    # lrtemplate=temlate_doc('learningresources')
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
                # returnjsonresult['score']=get_score(results,returnjsonresult['id'])
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
                    #normalized_content['authors']={"firstname": None,"lastname": None}
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
    ;;field:{"name":"usage_rights","type":"string","example":"USGS","description":""}
    ;;field:{"name":"citation","type":"string","example":"research","description":""}
    ;;field:{"name":"locator_data","type":"string","example":"\\\"10.5281/zenodo.239090\\\"","description":""}
    ;;field:{"name":"locator_type","type":"string","example":"DOI","description":""}
    ;;field:{"name":"publisher","type":"string","example":"\\\"Oak Ridge National Laboratory\\\"","description":""}
    ;;field:{"name":"version","type":"string","example":"\\\"1.0\\\"","description":""}
    ;;field:{"name":"access_features","type":"string","example":"Transformation","description":""}
    ;;field:{"name":"language_primary","type":"string","example":"es","description":""}
    ;;field:{"name":"languages_secondary","type":"string","example":"fr","description":""}
    ;;field:{"name":"ed_frameworks.name","type":"string","example":"\\\"FAIR Data Principles\\\"","description":""}
    ;;field:{"name":"ed_frameworks.nodes","type":"string","example":"Local Data Management","description":""}
    ;;field:{"name":"target_audience","type":"string","example":"\\\"Research scientist\\\"","description":""}
    ;;field:{"name":"purpose","type":"string","example":"\\\"Professional Development\\\"","description":""}
    ;;field:{"name":"completion_time","type":"string","example":"\\\"1 hour\\\"","description":""}
    ;;field:{"name":"media_type","type":"string","example":"\\\"Moving Image\\\"","description":""}
    ;;field:{"name":"type","type":"string","example":"\\\"Learning Activity\\\"","description":""}
    ;;field:{"name":"limit","type":"int","example":"15","description":"Maximum number of results to return. Default is 10"}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:{"search": [{"group": "and","and": [{"field": "keywords","string": "ethics","type": "simple"},{"field": "created","string": "2019-05-20T17:33:18Z","type": "gte"} ],"or": [{"field": "submitter_name","string": "Karl","type": "simple"}]}],"limit": 10,"offset": 5, "sort":"id asc"}
    {"search":[{"group":"and","and":[{"string":"Data archiving","field":"keywords","type":"match"}]}]}
    """
    if document is None:
        document = 'search.json'
    allowed_documents = ['search.json', 'documentation.html',
                         'documentation.md', 'documentation.htm', 'search.jsonld']

    if document not in allowed_documents:
        return render_template('bad_document.html', example="search.json"), 400

    if request.method == 'GET':
        if "search" not in document:
            return generate_documentation(learning_resources.__doc__, document, request, True)

        searchstring = "*:*"
        #searchstring = "status:true"
        searchstring = append_searchstring(searchstring, request, "title")
        searchstring = append_searchstring(searchstring, request, "url")
        searchstring = append_searchstring(
            searchstring, request, "access_cost")
        searchstring = append_searchstring(
            searchstring, request, "submitter_name")
        searchstring = append_searchstring(
            searchstring, request, "submitter_email")
        searchstring = append_searchstring(searchstring, request, "contributors.givenName")
        searchstring = append_searchstring(searchstring, request, "contributors.familyName")
        searchstring = append_searchstring(searchstring, request, "creator")
        searchstring = append_searchstring(searchstring, request, "author_org")
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
            searchstring, request, "usage_rights")
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
        searchstring = append_searchstring(searchstring, request, "type")
        searchstring = append_searchstring(searchstring, request, "author")
        searchstring = append_searchstring(searchstring, request, "id")

        rows = 10
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
        results = resources.search(searchstring,  fl="*,score", rows=rows)
        newresults = resources.search(searchstring, fl="id",rows=rows, start=start)
        newarray=[]
        for newres in newresults:
            newarray.append(newres['id'])

        session = Session(engine)
        sqlresults=session.query(Learningresources).filter(Learningresources.id.in_(newarray)).all()   
        if document == "search.jsonld":
            return format_resource_jsonld_fromdb(results,sqlresults)
        if document == "search.json":
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

            session = Session(engine)
            sqlresults=session.query(Learningresources).filter(Learningresources.id.in_(newarray)).all()   
            
            if returntype == "jsonld":
                return format_resource_jsonld_fromdb(results,sqlresults)
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


def add_timestamp(id,timestamp_type):
    now = datetime.now()
    nowstr=now.strftime("%Y-%m-%dT%H:%M:%SZ")
    #If id does not create it with new timestamp_type entry
    tsresult=timestamps.search("id:"+id)
    if len(tsresult)==0:
        timestamp_json = json.loads('{ "id":"'+id+'"}')
        timestamp_json[timestamp_type]=[nowstr]
        #print(timestamp_json)
        timestamps.add([timestamp_json])
        timestamps.commit()
        return("")
    else: #If it exists in timestamps, check if "timestamp_type" exists and update it with new timestamp_type entry
        timestamp_json=tsresult.docs[0]
        if timestamp_type in timestamp_json:#If access exists, then append...
            timestamp_json[timestamp_type].append(nowstr)
        else: #otherwise add it.
            timestamp_json[timestamp_type]=[nowstr]
        #print(timestamp_json)
        timestamps.add([timestamp_json])
        timestamps.commit()
        return("")


def check_urls():
    resourcelist = resources.search("*:*", fl="id,url", rows=100000)
    for resource in resourcelist:
        print("VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV")
        print(resource["url"])
        r = requests.head(resource["url"],allow_redirects=True)
        if r.status_code == 200:
            
            add_timestamp(resource["id"],"success")
        else:
            print("########################################################")
            print(r.status_code)
            print('Web site does not exists!')
            print(resource["id"]) 
            add_timestamp(resource["id"],"fail")
    #time.sleep(10)
@app.route("/admin/urlcheck/",  methods=['GET'])
def urlcheck():
   
    if current_user.is_authenticated:
        if "admin" in current_user.groups:
            print("starting stuff")
            linkcheck = threading.Thread(target=check_urls)
            linkcheck.start()
            print("returning stuff")
            return("You are admin")

        else:
            return("You must be admin")
    else:
        return("You must be a logged in as admin to start a check.")
   
@app.route("/api/access/<id>", methods=['GET'])
def access(id): #fart
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

    idresults = resources.search("id:"+id, fl="id")
    #If the id exists as a resource...
    if len(idresults)>0:
        add_timestamp(id,"access")
    #else return id not found.. 
    else:
        return("ID not found")
    return ''

@app.route("/api/vocabularies/", defaults={'document': None}, methods=['GET'])
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
                results = taxonomies.search(searchstring)
                for result in results:
                    result.pop('_version_', None)
                    returnval["results"].append(result)
                returnval['hits'] = results.hits
                returnval['hits-returned'] = len(results)
                return returnval
        else:
            returnval = json.loads(
                '{ "documentation":"'+request.host_url+'api/vocabularies/documentation.html","results":[]}')
            results = taxonomies.search("*:*")
            for result in results:
                result.pop('_version_', None)
                returnval["results"].append(result)
            returnval['hits'] = results.hits
            returnval['hits-returned'] = len(results)
            return returnval


@app.route("/login/", methods=['POST'])
def login():
    """ 
    GET:
        Validates credentials of users and creates and stores a session.
        Form Request: 

            username (string):  The users username.
            password (string):  The users password.
        Returns: 
            cookie:session token
    """
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
    return "DMT Clearinghouse."

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

@app.route("/user/<action>", methods=['POST'])
def user(action):
    #return action
    returnjson={"status":"success"}
    usercontent=None
    if request.is_json:
        usercontent = request.get_json()
    if usercontent:
        if action=="add":
            if all (key in usercontent for key in ("name","email")):
                if len(usercontent['name'])>0 and len(usercontent['email'])>0:

                    results = users.search("name:\""+usercontent['name']+"\"", rows=1)
                    if len(results.docs)==0:
                        emailresults = users.search("email:\""+usercontent['email']+"\"", rows=1)
                        if len(emailresults.docs)==0:
                            hashpw=None
                            groups=None
                            enabled=True
                            timezone="America/Denver"
                            if "password" in usercontent:
                                hashpw=drash.encode(usercontent["password"])
                            else:
                                hashpw=drash.encode(randomString(20))
                            if "groups" in usercontent:
                                if validate_groups(usercontent["groups"]):
                                    groups=usercontent["groups"]
                                else:
                                    groups=["submitter"]
                            else:
                                groups=["submitter"]
                            if "timezone" in usercontent:
                                if validate_timezone(usercontent["timezone"]):
                                    timezone=usercontent["timezone"]
                            if "enabled" in usercontent:
                                enabled=usercontent["enabled"]
                            email=usercontent['email']
                            name=usercontent['name']
                            userjson={
                                    "hash":hashpw,
                                    "name":name,
                                    "email":email,
                                    "timezone":timezone,
                                    "groups":groups,
                                    "enabled":enabled,
                                    "id":str(uuid.uuid4())
                                    }
                            print(userjson)
                            out=users.add([userjson])
                            test = users.commit()
                            print(out)
                            print(test)

                            msg = EmailMessage()
                            msg.set_content("Message goes here")

                            msg['Subject'] = 'An account for '+request.host_url+' has been created.'
                            msg['From'] = 'noreply@'+request.host_url
                            msg['To'] = email

                            s = smtplib.SMTP('localhost')
                            s.send_message(msg)
                            s.quit()

                        else:
                            return({"status":"error","message":"user \'"+emailresults.docs[0]["name"]+"\' with email "+usercontent['email']+" already exists. No action taken."})
                    else:
                        return({"status":"error","message":"user "+usercontent['name']+" already exists. No action taken."})
                else:
                    return({"status":"error","message":"To create a user both name and email need to be provided."})
            else:
                return({"status":"error","message":"To create a user both name and email keys need to be in json provided."})

    return(returnjson)
@app.route("/static/<path:path>")
def send_static(path):
    return send_from_file('static', path)


if __name__ == "__main__":
    app.run()
