from flask import Flask, request, redirect, url_for, render_template, make_response, session
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
import sys
from flask_cors import CORS
import copy

from flask.sessions import SecureCookieSessionInterface

import logging
logging.basicConfig()
logger = logging.getLogger('gstore_v3')
logger.setLevel(logging.INFO)

sys.path.append("/opt/DMTClearinghouse/")


# Create flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
CORS(app,supports_credentials=True)
session_cookie = SecureCookieSessionInterface().get_signing_serializer(app)

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



resources_facets = ["facet_authors.givenName","facet_authors.familyName","facet_author_org.name", "facet_subject", "facet_keywords", "facet_license", "facet_usage_info", "facet_publisher",
                    "facet_accessibility_features.name","facet_language_primary", "facet_languages_secondary", "facet_ed_frameworks.name","facet_author_names", "facet_ed_frameworks.nodes.name", "facet_target_audience", "facet_lr_type", "facet_purpose", "facet_media_type","facet_access_cost","facet_status","facet_pub_status"]
# Create a pysolr object for accessing the "learningresources" and "users" index
resources = pysolr.Solr(
    app.config["SOLR_ADDRESS"]+"learningresources/", timeout=10)
users = pysolr.Solr(app.config["SOLR_ADDRESS"]+"users/", timeout=10)
taxonomies = pysolr.Solr(app.config["SOLR_ADDRESS"]+"taxonomies/", timeout=10)
timestamps = pysolr.Solr(app.config["SOLR_ADDRESS"]+"timestamps/", timeout=10)
feedback = pysolr.Solr(app.config["SOLR_ADDRESS"]+"feedback/", timeout=10)
questions = pysolr.Solr(app.config["SOLR_ADDRESS"]+"questions/", timeout=10)
question_groups = pysolr.Solr(app.config["SOLR_ADDRESS"]+"question_groups/", timeout=10)
surveys = pysolr.Solr(app.config["SOLR_ADDRESS"]+"surveys/", timeout=10)
answers = pysolr.Solr(app.config["SOLR_ADDRESS"]+"answers/", timeout=10)



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


#This should add the cookie to the response.
@app.after_request
def cookies(response):
    session_cookie = SecureCookieSessionInterface().get_signing_serializer(app)
    same_cookie = session_cookie.dumps(dict(session))
    response.headers.add("Set-Cookie", f"session={same_cookie}; Secure; HttpOnly; SameSite=None; Path=/;")
    return response

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

def addFacets(j):
    r = requests.get(app.config["SOLR_ADDRESS"] +"learningresources/schema?wt=json")
    if r.json():
        for field in r.json()['schema']['fields']:
            if field['name'].startswith(('facet_')):
                non_facet_key=field['name'][len('facet_'):]
                if non_facet_key in j:
                    j[field['name']]=j[non_facet_key]
               
    
    return j





def insert_new_resource(j):


    j['creator']=current_user.name
    j=UpdateFacets(j)
    j['id']=str(uuid.uuid4())
    j['pub_status']="in-process"
    now_str=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    j['modification_date']=now_str
    j['created']=now_str
    j['published']=now_str
    j['rating']=0.0
    j['status']=0
    
    if 'contributor_orgs' in j:
        for contributor_org in j['contributor_orgs']:
            if 'name_identifier' in contributor_org:
                if 'name_identifier_type' not in contributor_org:
                    contributor_org['name_identifier_type']='N.A.'
                else:
                    if contributor_org['name_identifier_type']=='':
                        contributor_org['name_identifier_type']='N.A.'

    user_info = users.search("id:\""+current_user.id+"\"", rows=1)
    j['submitter_email']=user_info.docs[0]['email']
    j['submitter_name']=user_info.docs[0]['name']

    j2 = copy.deepcopy(j)
    j=addFacets(j)

    
    # db.session.add(Learningresources(id = j['id'], value=json.dumps(j)))
    try:
        db.session.add(Learningresources(id = j['id'], value=json.dumps(j)))
   
        x=resources.add([j])

        test = resources.commit()

        db.session.commit()
    
        add_timestamp(j['id'],"add new resource",current_user,request)
        return({"status":"success","doc":j2})
    except Exception as err:
        db.session.rollback()
        db.session.flush()
        return({"status":"fail","error":str(err)})

    


def UpdateFacets(j):
    for key in ["publisher","author_org.name","language_primary","license","target_audience","lr_type","accessibility_features.name","author_names","languages_secondary","ed_frameworks.nodes.name","purpose","usage_info","keywords","media_type","ed_frameworks.name","access_cost","subject","status","pub_status"]:
        if key in j.keys():
            j['facet_'+key]=j[key]
    return j

def update_resource(j):
    print("update resource")
    results = resources.search("id:"+j["id"], rows=1)
    doc={}
    if len(results.docs) > 0:
        doc=results.docs[0]
    else:
        return{"status":"error","message":"Invalid ID"},400
    current_status=doc['pub_status']
        # now_str=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    
    status=j['pub_status']
    if status not in ['in-process','published','in-review','deprecate-request','pre-pub-review','deprecated']:
        return{"status":"error","message":"status must be one of 'in-process','in-review','published', or 'deprecate-request'"},400

    #If contributor_orgs.name_identifier then contributor_orgs.name_identifier_type must be present "N.A." if not:
    if 'contributor_orgs' in j:
        for contributor_org in j['contributor_orgs']:
            if 'name_identifier' in contributor_org:
                if 'name_identifier_type' not in contributor_org:
                    contributor_org['name_identifier_type']='N.A.'
                else:
                    if contributor_org['name_identifier_type']=='':
                        contributor_org['name_identifier_type']='N.A.'



    can_edit=False
    if "admin" in current_user.groups:
        can_edit=True
    elif "editor" in current_user.groups:
        can_edit=True
    elif "reviewer" in current_user.groups:
        if status in ['pre-pub-review','deprecate-request','in-process','in-review'] and current_status not in ['published','deprecated']:
            can_edit=True
    elif "submitter" in current_user.groups :
        if status ==['in-review','in-process'] and current_status =='in-process':
            can_edit=True
    #elif "submitter"
    if can_edit:
        if status=='published':
            this_doc_orgs=[]
            this_doc_given_names=[]
            this_doc_family_names=[]
            this_doc_keywords=[]
            
            if 'author_org' in j:
                if 'name' in j['author_org']:
                    if j['author_org']['name'] not in this_doc_orgs:
                        this_doc_orgs.append(j['author_org']['name'])
            if 'contributor_orgs' in j:
                for contributor_org in j['contributor_orgs']:
                    if 'name' in contributor_org:
                        if contributor_org['name'] not in this_doc_orgs:
                            this_doc_orgs.append(contributor_org['name'])

            if 'authors' in j:
                for obj in j['authors']:
                    if obj['givenName'] not in this_doc_given_names:
                        this_doc_given_names.append(obj['givenName'])
                    if obj['familyName'] not in this_doc_family_names:
                        this_doc_family_names.append(obj['familyName'])
            if 'contributors' in j:
                for obj in j['contributors']:
                    if obj['givenName'] not in this_doc_given_names:
                        this_doc_given_names.append(obj['givenName'])
                    if obj['familyName'] not in this_doc_family_names:
                        this_doc_family_names.append(obj['familyName'])

            
            if 'keywords' in j:
                for kw in j['keywords']:
                    if kw not in this_doc_keywords:
                        this_doc_keywords.append(kw)


            res_taxonomies=taxonomies.search("name:Organizations",rows=1)
            vocabjson = res_taxonomies.docs[0]

            res_given_names=taxonomies.search("name:given_names",rows=1)
            res_given_names_json = res_given_names.docs[0]
            
            res_family_names=taxonomies.search("name:family_names",rows=1)
            res_family_names_json = res_family_names.docs[0]

            res_keywords=taxonomies.search("name:Keywords",rows=1)
            res_keywords_json = res_keywords.docs[0]

            res_media_types=taxonomies.search('name:"Media Type"',rows=1)
            res_media_types_json = res_media_types.docs[0]
            

            current_names=vocabjson['values']
            current_given_names=res_given_names_json['values']
            current_family_names=res_family_names_json['values']
            current_keywords= res_keywords_json['values']
            current_media_types= res_media_types_json['values']

            if 'media_type' in j:
                if j['media_type'] not in current_media_types:
                    res_media_types_json['values'].append(j['media_type'])
            
                res_media_types_json.pop("_version_", None)
                newvocabjson={'id':res_media_types_json['id'],'name':res_media_types_json['name'],'values':res_media_types_json['values'],'type':""}
                taxonomies.add([newvocabjson])
                taxonomies.commit()

            for kw in this_doc_keywords:
                if kw not in current_keywords:
                     res_keywords_json['values'].append(kw)

            res_keywords_json.pop("_version_", None)
            newvocabjson={'id':res_keywords_json['id'],'name':res_keywords_json['name'],'values':res_keywords_json['values'],'type':""}
            taxonomies.add([newvocabjson])
            taxonomies.commit()

            for name in this_doc_orgs:
                if name not in current_names:
                    vocabjson['values'].append(name)


            vocabjson.pop("_version_", None)
            if "type" in vocabjson:
                    vocabtype=vocabjson['type']
            else:
                vocabtype=""
            newvocabjson={'id':vocabjson['id'],'name':vocabjson['name'],'values':vocabjson['values'],'type':""}
            taxonomies.add([newvocabjson])
            taxonomies.commit()

            #Update names
            for name in this_doc_given_names:
                if name not in current_given_names:
                    res_given_names_json['values'].append(name)
            res_given_names_json.pop("_version_", None)
            #print(res_given_names_json['values'])
            if "type" in res_given_names_json:
                    vocabtype=res_given_names_json['type']
            else:
                vocabtype=""
            newvocabjson={'id':res_given_names_json['id'],'name':res_given_names_json['name'],'values':res_given_names_json['values'],'type':""}
            taxonomies.add([newvocabjson])
            taxonomies.commit()

            for name in this_doc_family_names:
                if name not in current_family_names:
                    res_family_names_json['values'].append(name)
            res_family_names_json.pop("_version_", None)
            if "type" in res_family_names_json:
                    vocabtype=res_family_names_json['type']
            else:
                vocabtype=""
            newvocabjson={'id':res_family_names_json['id'],'name':res_family_names_json['name'],'values':res_family_names_json['values'],'type':""}
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
        j['modification_date']=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        db.session.query(Learningresources).filter(Learningresources.id == j['id']).update({Learningresources.value:json.dumps(j)}, synchronize_session = False)

        j=UpdateFacets(j)
        result1=resources.search("id:"+j['id'], rows=1)
        timestamp_status="update"
        try:
            resources.add([j])
            resources.commit()
            db.session.commit()
            add_timestamp(j['id'],timestamp_status,current_user,request)
        except Exception as err:
            db.session.rollback()
            db.session.flush()
            return({"status":"fail","error":str(err)})
    else:
        return{"status":"error","message":"You do not have permisson to set pub_status to "+status},400
    return({"status":"success","doc":j})

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
                           'api/resources/documentation.html"}')
    returnval['hits-total'] = results.hits
    returnval['hits-returned'] = len(results)
    returnval["facets"]={}
    if "facet_fields" in results.facets.keys():
        returnval['facets']=fixFacets(results)
    returnval['results']=[]
    ids=[]
    for solrres in results:
        ids.append({'title':solrres['title'],'id':solrres['id']})
    returnval['results']=ids
    return returnval


def fixFacets(results):
    facets=results.facets['facet_fields']
    rfobject= {}
    for facet in facets:
        rfobject[facet.replace('facet_', '')]=facets[facet]
    for facet in rfobject:
        data_list={}
        index=0
        isKey=True
        for data in rfobject[facet]:
            if isKey:
              
                keyname=data.strip()
                isKey=False
            else:
                
                if len(keyname.strip())>0:
                    data_list[keyname]=data
                isKey=True
        rfobject[facet]=data_list
    return rfobject


def format_resource_fromdb(results,sqlresults):
    lrtemplate=temlate_doc('learningresources')
    returnval = json.loads('{ "documentation":"'+request.host_url +
                           'api/resources/documentation.html"}')
    returnval['hits-total'] = results.hits
    returnval['hits-returned'] = len(results)
    returnval["facets"]= {}
    if "facet_fields" in results.facets.keys():
        returnval['facets']=fixFacets(results)
    returnval['results']=[]
    for solrres in results:
        for result in sqlresults:
            returnjsonresult=json.loads(result.value)
            list_keys = list(returnjsonresult.keys())
            for k in list_keys:
                if k.startswith('facet_'):
                    returnjsonresult.pop(k)
                if k=='notes':
                    returnjsonresult.pop(k)
            if returnjsonresult["id"]==solrres['id']:
                returnjsonresult['score']=get_score(results,returnjsonresult['id']) 
                returnjsonresult['rating']=solrres['rating']
                returnjsonresult['ratings']=get_ratings(solrres['id'])
                returnval['results'].append(returnjsonresult)


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


def resource_metadata(collection_name):
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

@app.errorhandler(401)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('401.html'), 401


# Re-Index from MySQL
@app.route("/api/admin/reindex/", methods=['GET'])
@login_required
def reindex_from_mysql():
    
    # retval = json.loads('{}')
    return reindex()

# Unit Tests Route
@app.route("/api/admin/tests/", methods=['GET'])
@login_required
def unit_tests():
    # solr_to_mysql()
    tests = json.loads('{}')
    return tests


def get_ratings(id):
    resourceresult = resources.search("id:"+id, rows=1)
    thisresource=resourceresult.docs[0]
    feedbackresults=feedback.search("resourceid:"+id, rows=100000000)
    ratings=[]
    for result in feedbackresults:
        if 'rating' in result.keys():
            ratings.append(result["rating"])
    return ratings

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




@app.route("/api/questions/", defaults={'document': None}, methods=['GET','POST'])
@app.route("/api/questions/<document>", methods=['GET', 'POST'])
@login_required
def question_func(document):
    """ 
    GET:
        Builds Documentation

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Updates or creates a question.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr 
    PUT
        Will not be implemented
    DELETE
        Not yet implemented



    ;;field:{"name":"label","type":"string","example":"\\\"Is the purpose of the resource clear?\\\"","description":"The question label."}
    ;;field:{"name":"element","type":"string","example":"select","description":"type of element(select,input, etc.)"}
    ;;field:{"name":"id","type":"string","example":"IDPLACEHOLDER","description":"The ID of the question."}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:{}"""

    if request.method == 'GET':
        
        this_docstring = question_func.__doc__
        if document is not None:
            allowed_documents = ['documentation.html',
                                    'documentation.md', 'documentation.htm']
            if document not in allowed_documents:
                return render_template('bad_document.html', example="documentation.html"), 400
            else:
                print("else")
                result1 = questions.search("*:*", rows=1)
                id = result1.docs[0]["id"]
                this_docstring = this_docstring.replace('IDPLACEHOLDER', id)
                
                return generate_documentation(this_docstring, document, request, True)
        else:

            searchstring="*:*"
            searchstring = append_searchstring(searchstring, request, "label")
            searchstring = append_searchstring(searchstring, request, "id")
            searchstring = append_searchstring(searchstring, request, "element")
            print(searchstring)
            obj={'questions':[]}
            q=questions.search(searchstring,rows=100000)
            for qs in q:
                # question_ids:ef29fc71-bc49-4f8f-83ba-2beeafe4cd3c
                q_in_group=question_groups.search("question_ids:"+qs['id'])
                if len(q_in_group.docs)>0:
                    qs['protected']=True
                else:
                    qs['protected']=False
                if qs['element']=='select':
                    opt_arr=[]
                    for opt_string in qs['options']:
                        if isinstance(opt_string, str):
                            opt_arr.append(json.loads(opt_string.replace('\'','"')))
                        else:
                            opt_arr.append(opt_string)
                    qs['options']=opt_arr
                qs.pop('_version_', None)    
                obj['questions'].append(qs)
            return obj
    
    if request.method == 'POST':
        content = request.get_json()
        if document=="add":
            if 'id' in content.keys():
                q_in_group=question_groups.search("question_ids:"+content['id'])
                if len(q_in_group.docs)>0:
                   return {'status':'fail','message':'Question is part of existing question group'}

            insertobj={}

            insertobj['timestamp']=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            if request.is_json:
                content = request.get_json()
                if 'label' in content.keys() and 'name' in content.keys() and 'input_type' in content.keys() and 'options' in content.keys() and 'element' in content.keys() and 'id' not in content.keys(): #add
                    print("add")
                    insertobj['label']=content['label']
                    insertobj['name']=content['name']
                    insertobj['element']=content['element']
                    insertobj['options']=content['options']
                    insertobj['input_type']=content['input_type']
                    insertobj=json.loads(json.dumps(insertobj))
                    try:
                        questions.add([insertobj])
                        questions.commit()
                        q=questions.search("name:"+content['name'],rows=1)
                        return{"status":"success","message":str(q.docs[0]['id'])}
                    except Exception as e:
                        return{"status":"error","message":"Question Insert Failed:"+str(e)}
                elif 'label' in content.keys() and 'name' in content.keys() and 'input_type' in content.keys() and 'options' in content.keys() and 'element' in content.keys() and 'id' in content.keys(): #update

                    q_in_group=question_groups.search("question_ids:"+content['id'])
                    if len(q_in_group.docs)>0:
                        return{"status":"error","message":"Question Update Failed. Question Exists in Existing Question Group."}
                                                                                                      
                    insertobj['label']=content['label']
                    insertobj['name']=content['name']
                    insertobj['element']=content['element']
                    insertobj['options']=content['options']
                    insertobj['input_type']=content['input_type']
                    insertobj['id']=content['id']
                    try:
                        questions.add([insertobj])
                        questions.commit()
                        return{"status":"success","message":"Question Updated Successfully."}
                    except:
                        return{"status":"error","message":"Question Update Failed."}
                else:
                    return{"status":"error","message":"submitted json not well formed."}
        if document=="delete":
            if 'id' in content.keys(): 
                q_in_group=question_groups.search("question_ids:"+content['id'])
                if len(q_in_group.docs)>0:
                   return {'status':'fail','message':'Question is part of existing question group'}
                else:
                    q='id:'+content['id']
                    questions.delete(q=q)
                    questions.commit()
                    return {'status':'success','message':'id:'+content['id']+" removed."}
            return {'status':'fail','message':'id key not found'}

    


@app.route("/surveytest/<survey_id>", methods=['GET'])
def surveytest(survey_id):
    return render_template('surveytest.html', survey_id=survey_id)



@app.route("/api/submit_survey/<survey_id>", methods=['POST'])
def submit_survey(survey_id):
    surveys_result1 = surveys.search("id:"+survey_id, rows=1)
    resourceid=surveys_result1.docs[0]['resourceid']
    survey_label=surveys_result1.docs[0]['label']
    is_default=False
    if survey_label=='Default':
        is_default=True
    result1 = resources.search("id:"+resourceid, rows=1)
    resource_doc = result1.docs[0]
    resource_doc.pop("_version_", None)
    if request.get_json() is None:
        form_answers=request.form.to_dict(flat=False)
        average_list=[]
        for key in form_answers.keys():
            answers_list=[]
            if key!='submitter': 
                if form_answers[key][0].isdigit():
                    form_answers[key][0]=int(form_answers[key][0])
                obj={'surveys_id':survey_id,'respondent_id':form_answers['submitter'][0],"question_id":key,"answer":form_answers[key][0]}

                if form_answers[key][0].isnumeric():
                    average_list.append(float(form_answers[key][0]))

                answers_list.append(obj)
            answers.add(answers_list)
            answers.commit()
            print(json.dumps(answers_list))
        average=sum(average_list) / len(average_list)

        if 'ratings' in resource_doc:
            resource_doc['ratings'].append(average)
            resource_doc['rating']=sum(resource_doc['ratings']) / len(resource_doc['ratings'])
        else:
            resource_doc['ratings']=[average]
            resource_doc['rating']=average

        try:
            if is_default:
                resources.add([resource_doc])
                resources.commit()
            return({"status":"success","message":"survey submitted successfully."})
        except Exception as e:
            return({"status":"fail","message":str(e)})

        return({"status":"success","message":"survey submitted successfully."})
    else:
        answers_json=request.get_json()
        for jkey in ["respondent_id","answers"]:
            if jkey not in answers_json.keys():
                return({"status":"fail","message":jkey+" missing."})
        answers_list=[]
        average_list=[]
        for answer in answers_json["answers"]:
            if answer['answer'].isnumeric():
                average_list.append(float(answer['answer']))

            answer["surveys_id"]=survey_id
            answer["respondent_id"]=answers_json["respondent_id"]
            answers_list.append(answer)
        average=sum(average_list) / len(average_list)
        if 'ratings' in resource_doc:
            resource_doc['ratings'].append(average)
            resource_doc['rating']=sum(resource_doc['ratings']) / len(resource_doc['ratings'])
        else:
            resource_doc['ratings']=[average]
            resource_doc['rating']=average
        try:
            answers.add(answers_list)
            answers.commit()
            if is_default:
                resources.add([resource_doc])
                resources.commit()
            return({"status":"success","message":"survey json submitted successfully."})
        except Exception as e:
            return({"status":"fail","message":str(e)})
        



@app.route("/api/survey_responses/<outtype>/", methods=['GET'])
def survey_responses_param(outtype):
    survey_id=request.args.get('survey_id')
    if survey_id:
        return survey_responses(outtype,survey_id)
    else:
        return{'status':'error','message':'survey_id must be specified.'}

@app.route("/api/survey_responses/<outtype>/<survey_id>", methods=['GET'])
def survey_responses(outtype,survey_id):
    answers_obj={'answers':[]}
    typelist=['answers','questions','respondents']
    answers_search=answers.search("surveys_id:"+survey_id, sort="respondent_id desc",rows=10000000)
    if outtype in typelist:
        if outtype=="answers": 
            for answer in answers_search:
                q=questions.search("id:"+answer['question_id'],rows=1)
                answer['label']=q.docs[0]['label']
                if q.docs[0]['element']=='select':
                    for opt in q.docs[0]['options']:
                        obj_json=json.loads(json.dumps(opt).replace("\"", '').replace("'", '"'))
                        if int(obj_json['value'])==int(answer['answer']):
                            answer['answer_text']=obj_json['key']
                    answer['answer']=int(answer['answer'])
                else:
                    answer['answer_text']=answer['answer']
                answers_obj['answers'].append(answer)
        elif outtype=="questions":
            placeholder={}
            for answer in answers_search:
                    print(answer)
                    q=questions.search("id:"+answer['question_id'],rows=1)
                    if q.docs[0]['id'] not in placeholder:
                        placeholder[q.docs[0]['id']]={'question_id':q.docs[0]['id'],"label": q.docs[0]['label'],"answers": [],"answers_text": [],"respondent_ids": [],}
                    placeholder[q.docs[0]['id']]['type']=q.docs[0]['element']
                    if q.docs[0]['element']=='select':
                        max_val=0
                        min_val=10000000
                        all_possible=[]
                        for opt in q.docs[0]['options']:
                            obj_json=json.loads(json.dumps(opt).replace("\"", '').replace("'", '"'))
                            
                            if int(obj_json['value'])>max_val:
                                max_val=int(obj_json['value'])
                            if int(obj_json['value'])<min_val:
                                min_val=int(obj_json['value'])
                            if int(obj_json['value']) not in all_possible:
                                all_possible.append(int(obj_json['value']))
                            if int(obj_json['value'])==int(answer['answer']):
                                placeholder[q.docs[0]['id']]['answers_text'].append(obj_json['key'])
                        placeholder[q.docs[0]['id']]['answers'].append(int(answer['answer']))
                        placeholder[q.docs[0]['id']]['max_score']=max_val
                        placeholder[q.docs[0]['id']]['min_score']=min_val
                        placeholder[q.docs[0]['id']]['possible_scores']=all_possible

                        placeholder[q.docs[0]['id']]['respondent_ids'].append(answer['respondent_id'])
                    else:
                        placeholder[q.docs[0]['id']]['answers'].append(answer['answer'])
                        placeholder[q.docs[0]['id']]['answers_text'].append(answer['answer'])
                        placeholder[q.docs[0]['id']]['respondent_ids'].append(answer['respondent_id'])
            for placeholder_key in placeholder:
                if placeholder[placeholder_key]['type']=='select':
                    placeholder[placeholder_key]['average']=sum(placeholder[placeholder_key]['answers'])/len(placeholder[placeholder_key]['answers'])
                else:
                    placeholder[placeholder_key]['average']=None
                answers_obj['answers'].append(placeholder[placeholder_key])
        elif outtype=="respondents":


            placeholder={}
            for answer in answers_search:
                this_question=questions.search("id:"+answer['question_id'],rows=1)
                if answer['respondent_id'] not in placeholder:
                        placeholder[answer['respondent_id']]={'respondent_id':answer['respondent_id'],"questions_and_answers":[]}
                q_n_a={"question":this_question.docs[0]['label']}
                if this_question.docs[0]['element']=='select':
                    q_n_a['answer']=int(answer['answer'])
                    new_dict={}
                    for opt in this_question.docs[0]['options']:
                        obj_json=json.loads(json.dumps(opt).replace("\"", '').replace("'", '"'))
                        new_dict[int(obj_json['value'])]=obj_json['key']
                    q_n_a['answer_text']=new_dict[int(answer['answer'])]
                else:
                    q_n_a['answer']=answer['answer']
                    q_n_a['answer_text']=answer['answer']
                placeholder[answer['respondent_id']]['questions_and_answers'].append(q_n_a)
                
            for placeholder_key in placeholder:
                answers_obj['answers'].append(placeholder[placeholder_key])
               




               
    else:
        return{'status':'error','message':'Unknown type '+ outtype+' specified'}



    return(answers_obj)

@app.route("/api/get_survey/<survey_id>", methods=['GET'])
def get_survey(survey_id):
    """ 
    GET:
        Builds Documentation

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Updates or creates a question.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr 
    PUT
        Will not be implemented
    DELETE
        Not yet implemented



    ;;field:{"name":"question","type":"string","example":"How usefull was this resource?","description":"The question label."}
    ;;field:{"name":"type","type":"string","example":"bool","description":"The queston type."}
    ;;field:{"name":"id","type":"string","example":"IDPLACEHOLDER","description":"The ID of the question."}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:"""
    surveys_result1 = surveys.search("id:"+survey_id, rows=1)
    groups=[]
    print("_________________________________")
    print(surveys_result1.docs)
    print("_________________________________")
    resourceid=surveys_result1.docs[0]['resourceid']
    for doc in surveys_result1.docs:
        for group_id in doc['question_group_ids']:
            print(group_id)


   
            group_obj={}
            question_groups_results=question_groups.search("id:"+group_id, rows=1)
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX1")
            print(question_groups_results.docs)
            print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX2")
            group_obj['label']=question_groups_results.docs[0]['label']
            group_obj['questions']=[]
            for question_id in question_groups_results.docs[0]['question_ids']:
                print(question_id)
                question_results=questions.search("id:"+question_id, rows=1)
                question_obj={'label':None,'name':None,'element':None,'options':[],'input_type':None}
                things=['label','name','element','options','input_type','id']
                for thing in things:
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print(question_results.docs)
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    if thing in question_results.docs[0].keys():
                        if thing=='options':
                            opt_arr=[]
                            for opt_str in question_results.docs[0][thing]:

                                opt_arr.append(json.loads(opt_str.replace("\'","\"")))
                            question_obj[thing]= opt_arr   
                        else:
                            question_obj[thing]=question_results.docs[0][thing]
        



                group_obj['questions'].append(question_obj)
            print(question_groups_results.docs[0]['question_ids'])
            groups.append(group_obj)
    print(groups)
    return_object={}
    return_object['label']=surveys_result1.docs[0]['label']
    return_object['question_groups']=groups
    return_object['resourceid']=resourceid
    return (return_object)



@app.route("/api/surveys/", defaults={'document': None}, methods=['GET'])
@app.route("/api/surveys/<document>", methods=['GET'])
def surveys_func_get(document):
    """ 
    GET:
        Builds Documentation

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Updates or creates a question.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr 
    PUT
        Will not be implemented
    DELETE
        Not yet implemented



    ;;field:{"name":"label","type":"string","example":"\\\"LABELPLACEHOLDER\\\"","description":"The survey label."}
    ;;field:{"name":"resourceid","type":"string","example":"RESOURCEIDPLACEHOLDER","description":"The resource that is associated with this survey."}
    ;;field:{"name":"id","type":"string","example":"SURVEYIDPLACEHOLDER","description":"The ID of the survey."}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:{"label": "LABELPLACEHOLDER","resourceid": "RESOURCEIDPLACEHOLDER", "id":"SURVEYIDPLACEHOLDER"}
    """
    
    if request.method == 'GET':
        this_docstring = surveys_func.__doc__
        if document is not None:
            allowed_documents = ['documentation.html',
                                    'documentation.md', 'documentation.htm']
            if document not in allowed_documents:
                return render_template('bad_document.html', example="documentation.html"), 400
            else:
                result1 = surveys.search("*:*", rows=1)
                resourceid = result1.docs[0]["resourceid"]
                label = result1.docs[0]["label"]
                id = result1.docs[0]["id"]
                this_docstring = this_docstring.replace('SURVEYIDPLACEHOLDER', id).replace('RESOURCEIDPLACEHOLDER', resourceid).replace('LABELPLACEHOLDER', label)

                
                return generate_documentation(this_docstring, document, request, True)
        else:
            searchstring="*:*"
            searchstring = append_searchstring(searchstring, request, "label")
            searchstring = append_searchstring(searchstring, request, "id")
            searchstring = append_searchstring(searchstring, request, "resourceid")
            obj={'surveys':[]}
            q=surveys.search(searchstring,rows=100000)
            for qs in q:
                
                q_in_group=answers.search("surveys_id:"+qs['id'])
                if len(q_in_group.docs)>0:
                    qs['protected']=True
                else:
                    qs['protected']=False

                qs.pop('_version_', None)
                obj['surveys'].append(qs)
            return obj



@app.route("/api/surveys/", defaults={'document': None}, methods=['POST'])
@app.route("/api/surveys/<document>", methods=['POST'])
@login_required
def surveys_func(document):
    """ 
    GET:
        Builds Documentation

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Updates or creates a question.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr 
    PUT
        Will not be implemented
    DELETE
        Not yet implemented



    ;;field:{"name":"label","type":"string","example":"\\\"LABELPLACEHOLDER\\\"","description":"The survey label."}
    ;;field:{"name":"resourceid","type":"string","example":"RESOURCEIDPLACEHOLDER","description":"The resource that is associated with this survey."}
    ;;field:{"name":"id","type":"string","example":"SURVEYIDPLACEHOLDER","description":"The ID of the survey."}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:{"label": "LABELPLACEHOLDER","resourceid": "RESOURCEIDPLACEHOLDER", "id":"SURVEYIDPLACEHOLDER"}
    """

    if request.method == 'POST':
        content = request.get_json()
        if document=="add":
            if 'id' in content.keys():
                q_in_group=answers.search("surveys_id:"+content['id'])
                if len(q_in_group.docs)>0:
                    {'status':'fail','message':'Cannot modify Survey as there are existing answers to this question.'}

            insertobj={}

            insertobj['timestamp']=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            if request.is_json:
                content = request.get_json()
                if 'id' in content:
                    q_in_group=answers.search("surveys_id:"+content['id'])
                    if len(q_in_group.docs)>0:
                        return{"status":"error","message":"Survey Update Failed. There Are Associated Questions that Exist."}

                if 'label' in content.keys() and 'question_group_ids' in content.keys() and 'resourceid' in content.keys() and 'id' not in content.keys(): #add
                    insertobj['label']=content['label']
                    insertobj['question_group_ids']=content['question_group_ids']
                    insertobj['resourceid']=content['resourceid']
                    newuuid=str(uuid.uuid4())
                    insertobj['id']=newuuid
                    surveys.add([insertobj])
                    surveys.commit()
                    return{"status":"success","message":newuuid}
                elif 'label' in content.keys() and 'question_group_ids' in content.keys() and 'resourceid' in content.keys() and 'id' in content.keys(): #update
                    insertobj['label']=content['label']
                    insertobj['question_group_ids']=content['question_group_ids']
                    insertobj['resourceid']=content['resourceid']
                    insertobj['id']=content['id']
                    try:
                        questions.add([insertobj])
                        questions.commit()
                        return{"status":"success","message":"Survey Updated Successfully."}
                    except:
                        return{"status":"error","message":"Survey Update Failed."}

                else:
                    return{"status":"error","message":"submitted json not well formed."}
        if document=="delete":
            if 'id' in content.keys():
                q_in_group=answers.search("surveys_id:"+content['id'])
                if len(q_in_group.docs)>0:
                    {'status':'fail','message':'Cannot remove Survey as there are existing answers to this question.'}
                else:
                    q='id:'+content['id']
                    surveys.delete(q=q)
                    surveys.commit()
                    return {'status':'success','message':'id:'+content['id']+" removed."}
            else:
                return {'status':'fail','message':'id key not found.'}
        if document is None:
            searchstring = "*:*"
            if request.is_json:
                content = request.get_json()
                if "label" in content:
                    searchstring=searchstring+" AND label:\""+content["label"]+"\""
                if "resourceid" in content:
                    searchstring=searchstring+" AND resourceid:"+content["resourceid"]
                if "id" in content:
                    searchstring=searchstring+" AND id:"+content["id"]                    
            print(searchstring)
            obj={'surveys':[]}
            q=surveys.search(searchstring,rows=100000)
            for qs in q:
                
                q_in_group=answers.search("surveys_id:"+qs['id'])
                if len(q_in_group.docs)>0:
                    qs['protected']=True
                else:
                    qs['protected']=False

                qs.pop('_version_', None)
                obj['surveys'].append(qs)
            return obj



@app.route("/api/question_groups/", defaults={'document': None}, methods=['GET','POST'])
@app.route("/api/question_groups/<document>", methods=['GET', 'POST'])
@login_required
def question_groups_func(document):
    """ 
    GET:
        Builds Documentation

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr  
    POST:
        Updates or creates a question.

        Parameters: 

            request (request):  The full request made to a route.

        Returns: 
            json: JSON results from Solr 
    PUT
        Will not be implemented
    DELETE
        Not yet implemented



    ;;field:{"name":"question","type":"string","example":"How usefull was this resource?","description":"The question label."}
    ;;field:{"name":"type","type":"string","example":"bool","description":"The queston type."}
    ;;field:{"name":"id","type":"string","example":"IDPLACEHOLDER","description":"The ID of the question."}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:"""

    if request.method == 'GET':
        
        this_docstring = addfeedback.__doc__
        if document is not None:
            allowed_documents = ['documentation.html',
                                    'documentation.md', 'documentation.htm']
            if document not in allowed_documents:
                return render_template('bad_document.html', example="documentation.html"), 400
            else:
                print("else")
                result1 = resources.search("*:*", rows=1)
                id = result1.docs[0]["id"]
                this_docstring = this_docstring.replace('IDPLACEHOLDER', id)
                
                return generate_documentation(this_docstring, document, request, True)
        else:

            obj={'question_groups':[]}
            q=question_groups.search("*:*")
            for qs in q:
                
                q_in_group=surveys.search("question_group_ids:"+qs['id'])
                if len(q_in_group.docs)>0:
                    qs['protected']=True
                else:
                    qs['protected']=False

                qs.pop('_version_', None)
                obj['question_groups'].append(qs)
            return obj

    if request.method == 'POST':
        content = request.get_json()
        if document=="add":
            if 'id' in content.keys(): 
                q_in_group=surveys.search("question_group_ids:"+content['id'])
                if len(q_in_group.docs)>0:
                    return {'status':'fail','message':'Question Group is part of existing Survey.'}
            insertobj={}

            insertobj['timestamp']=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            if request.is_json:
                content = request.get_json()
                if 'label' in content.keys() and 'question_ids' in content.keys() and 'id' not in content.keys(): #add
                    print("add")
                    insertobj['label']=content['label']
                    insertobj['question_ids']=content['question_ids']
              
                    search_str="label:\""+content['label']+'"'
                    q=question_groups.search(search_str,rows=1)
                    if len(q.docs)>0:
                        return{"status":"error","message":"Question Group label \'"+content['label']+"\' already exists."}
                    
                    question_groups.add([insertobj])
                    question_groups.commit()
                    q=question_groups.search(search_str,rows=1)
                    
                    return{"status":"success","message":str(q.docs[0]['id'])}

                    #return insertobj
                elif 'label' in content.keys() and 'question_ids' in content.keys() and 'id' in content.keys(): #update

                    qg_in_surveys=surveys.search("question_group_ids:"+content['id'])
                    if len(qg_in_surveys.docs)>0:
                        return{"status":"error","message":"Question Update Failed. Question Exists in Existing Question Group."}

                    print("???")
                    insertobj['label']=content['label']
                    insertobj['question_ids']=content['question_ids']
                    insertobj['id']=content['id']
                    try:
                        question_groups.add([insertobj])
                        question_groups.commit()
                        return{"status":"success","message":"Question Group Updated Successfully."}
                    except:
                        return{"status":"error","message":"Question Group Update Failed."}
                    
                    question_groups.add([insertobj])
                    question_groups.commit()
                    return insertobj
                else:
                    return{"status":"error","message":"submitted json not well formed."}
        if document=="delete":
            if 'id' in content.keys(): 
                q_in_group=surveys.search("question_group_ids:"+content['id'])
                if len(q_in_group.docs)>0:
                    return {'status':'fail','message':'Question Group is part of exiting Survey.'}
                else:
                    q='id:'+content['id']
                    question_groups.delete(q=q)
                    question_groups.commit()
                    return {'status':'success','message':'id:'+content['id']+" removed."}
            else:
                return {'status':'fail','message':'id key not found.'}

    



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

@app.route('/api/rss')
def rss():
    fg = FeedGenerator()
    fg.title('DMT Clearinghouse')
    fg.description('A registry for online learning resources focusing on research data management.')
    fg.id(request.base_url)
    fg.link( href=request.base_url, rel='self' )
    results=resources.search("status:True",sort="created desc",rows=10)
    retstr=''
    for resource in results.docs: 

        fe = fg.add_entry()
        fe.title(resource['title'])
        fe.link(href=resource['url'])
        fe.description(resource['abstract_data'])
        fe.guid(resource['id'], permalink=False)
        thisemail=app.config["RSS_EMAIL"]


        if 'author_names' in resource:
            if  len(resource['author_names'])>0:
                thisname=",".join(resource['author_names'])
            elif 'author_org.name' in resource:
                thisname=resource['author_org.name']
        elif 'author_org.name' in resource:
            thisname=resource['author_org.name']
        else:
            thisname='Unknown'
        retstr=retstr+":"+thisname
        fe.author(name=thisname, email=thisemail)

        
        fe.pubDate(resource['created'])

    response = make_response(fg.rss_str(pretty=True))
    response.headers.set('Content-Type', 'application/rss+xml')

    return response

# Resource interaction
@app.route("/api/resource/", defaults={'document': None}, methods=['PUT','POST','DELETE'])

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



    ;;field:{"name":"template","type":"","example":"true","description":"Generate empty resource from schema."}
    ;;field:{"name":"metadata","type":"","example":"true","description":"Generate metadata for all resource fields."}
    ;;field:{"name":"id","type":"string","example":"IDPLACEHOLDER","description":"The ID of the learning resource."}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:"""

    if request.method == 'POST':
        if request.is_json:
            content = request.get_json()
            if 'id' not in content or content['id']=="": #treat as if it is a new document
                    return insert_new_resource(content)
            else:
                return {'status':'error','message':"New documents cannot have an 'id' key."} 
                   # return update_resource(content)
        else:
            return {'status':'error','message':'POST must have a JSON body'}

    if request.method == 'PUT':
        if request.is_json:
            content = request.get_json()
            if 'id' not in content or content['id']=="": #treat as if it is a new document
                return {'status':'error','message':'Existing documents must have an "id" key.'} 
            else:
               return update_resource(content)
        else:
            return {'status':'error','message':'POST must have a JSON body'}

                
    if request.method == 'DELETE':
        content = request.get_json()
        if 'id' in content.keys(): 
            q='id:'+content['id']
            resources.delete(q=q)
            resources.commit()
            return {'status':'success','message':'id:'+content['id']+" removed."}
        else:
            return {'status':'error','message':'JSON body must have an "id" key to delete.'}


    return "Documentation not implemented."




# Resource interaction
@app.route("/api/pub_status/", defaults={'status': None}, methods=['POST'])
@app.route("/api/pub_status/<status>", methods=['GET', 'POST'])
@login_required
def pub_status(status):
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
        content = request.get_json()
        results = resources.search("id:"+content["id"], rows=1)
        doc={}
        if len(results.docs) > 0:
            doc=results.docs[0]
        else:
            return{"status":"error","message":"Invalid ID"},400
        current_status=doc['pub_status']
        if status in ['in-process','published','in-review','delete-request','pre-pub-review','deleted']:
            doc['pub_status']=status
            return update_resource(doc)

        else:
            #pub_status:in-process OR pub_status:published  OR pub_status:in-review
            return{"status":"error","message":"status must be one of 'in-process','in-review','published', or 'delete-request'"},400
                    
                

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
@app.route("/api/resource/<document>", methods=[ 'GET'])
def learning_resource(document):
    if request.method == "GET":
        print('get')
        if document is None:
            print(request.args.get('metadata'))
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
                    return normalized_content
                else:
                    return "No results found"
            elif request.args.get('template'):
                
                template = temlate_doc('learningresources')
                response = app.response_class(
                response=json.dumps(template),
                status=200,
                mimetype='application/json')
                return response
            elif request.args.get('metadata'):
                print('title')
                field_sets=[{'fields':[], 'name':'general','label':'General','contains':[]},
                {'fields':[], 'name':'access_constraints','label':'Access Constraints','contains':['access_cost','license','access_conditions']},
                {'fields':[], 'name':'accessibility','label':'Accessibility','contains':['accessibility_summary','accessibility_features.name']},
                {'fields':[], 'name':'authors','label':'Author(s)','contains':['author_names', 'authors.familyName', 'authors.givenName', 'author_org.name','author_org.name_identifier', 'author_org.name_identifier_type','authors.name_identifier', 'authors.name_identifier_type']},
                {'fields':[], 'name':'resource_contact','label':'Resource Contact','contains':['contact.org', 'contact.name', 'contact.email']},
                {'fields':[], 'name':'contributors','label':'Contributor(s)','contains':['contributors.familyName', 'contributors.givenName','contributor_orgs.name', 'contributor_orgs.type', 'contributors.type']},
                {'fields':[], 'name':'md_record','label':'MD Record','contains':[]},
                {'fields':[], 'name':'educational_information','label':'Educational Information','contains':['target_audience','lr_type','ed_frameworks.nodes.description', 'purpose', 'subject', 'ed_frameworks.name', 'ed_frameworks.nodes.name']},
                # {'fields':[], 'name':'access_conditions','label':'Access Conditions','contains':['license','access_conditions']},
                {'fields':[], 'name':'resource_location','label':'Resource Location','contains':['locator_data','locator_type']},
                ]

                    #[, 'abstract_data', 'citation', , , , 'name_identifier',  , 'title', , , , 'resource_modification_date', , 'usage_info', 'publisher', 
                    #'language_primary', 'languages_secondary', 'media_type', 'keywords', 
                    # 'credential_status', 'completion_time'']

                textarea=['access_conditions','abstract_data','citation','accessibility_summary','ed_frameworks.nodes.description','name_identifier','title','usage_info']
                text=['locator_type','locator_data','contact.org','contact.name','author_org.name_identifier',"authors.name_identifier","submitter_name","lr_outcomes"]
                user_identifier=["authors.name_identifier_type"]
                org_identifier=['author_org.name_identifier_type']
                dates=['resource_modification_date']
                yn_select=['access_cost']
                email=['contact.email','submitter_email']
                select_multiple_facet=["accessibility_features.name"]
                select_multiple_taxonomy=['languages_secondary','subject']
                facet_checkbox=[]
                facet_datalist=['license','media_type']
                taxonomy_datalist=['contributors.givenName','authors.givenName','contributors.familyName','authors.familyName']
                orgs=['author_org.name','contributor_orgs.name']
                flexdatalist=['keywords','publisher','ed_frameworks.name','author_names','target_audience']
                select_single_taxonomy=['language_primary','lr_type','purpose','expertise_level']#['ed_frameworks.nodes.name']
                yes_no_unknown=["credential_status"]
                #given_names=['contributors.givenName','authors.givenName']
                #family_names=['contributors.familyName','authors.familyName']
                # auto_gen=['authors.familyName','authors.givenName'] created

                taxonomy_field=['contributor_orgs.type','contributors.type']
                taxonomy_select_single_field=['completion_time']
                
                custom_labels={'lr_outcomes':'Learning Outcomes','ed_frameworks.name':'Educational Framework Name','subject':'Subject Discipline','abstract_data':'Abstract/Description','lr_type':'Learning Resource Type','authors.givenName':'Author(s) Given/First Name','authors.familyName':'Author(s) Family/Last Name','contributors.familyName':'Contributor(s) Family/Last Name','contributors.givenName':'Contributor(s) Given/First Name','url':'URL'}
                taxonomy_keys={'subject':'Subject Disciplines',  'purpose':'Educational Purpose', 'expertise_level':'expertise_level', 'language_primary':'languages', 'languages_secondary':'languages','contributors.givenName':'given_names','authors.givenName':'given_names','authors.familyName':'family_names','contributors.familyName':'family_names','author_org.name':'Organizations','contributor_orgs.name':'Organizations','lr_type':'Learning Resource Types','completion_time':'Completion Timeframes','contributor_orgs.type':'Contributor Types','contributors.type':'Contributor Types','accessibility_features.name':'Accessibility Features'}
                url=['url']
                required_obj={
                'Required':['abstract_data','access_cost','author_names','keywords','language_primary','','license','locator_data'
                ,'locator_type','lr_type','submitter_email','submitter_name','title','url','expertise_level','lr_outcomes']

                ,'Optional':['accessibility_features.name','accessibility_summary','completion_time','country_of_origin','credential_status','ed_frameworks.nodes.description',
                'ed_frameworks.nodes.name']

                ,'Recommended':['author_org.name_identifier','author_org.name_identifier_type','authors.givenName','authors.familyName','author_org.name',
                'authors.name_identifier','authors.name_identifier_type','citation','contact.name','contact.org','contributor_orgs.name','contributor_orgs.type'
                ,'contributors.givenName','contributors.familyName','contributors.type','creator','ed_frameworks.name','languages_secondary','media_type','resource_modification_date'
                ,'publisher','purpose','subject','','target_audience','target_audience','usage_info']}
                r=requests.get(request.host_url+'/api/resources/?limit=1&facet_limit=-1')
                facet_json=r.json()
                r2=requests.get(request.host_url+'/api/vocabularies/')
                

                vocabularies_json=r2.json()
                
                #build framework_nodes:
                framework_nodes={}
                for result in  vocabularies_json['results']:
                    if 'type' in result:
                        framework_nodes[result['name']]=result['values']
                      

                return_json={}
                return_json['ed_frameworks.nodes.name']={
                "label": "Educational Framework Nodes",
                "element": "select",
                "attributes": [
                "single"
                ],
                "name": "ed_frameworks.nodes.name",
                "taxonomy": False,
                "options":framework_nodes#[{'key': 'Accessible', 'value': 'Accessible'}, {'key': 'Findable', 'value': 'Findable'}, {'key': 'Interoperable', 'value': 'Interoperable'}, {'key': 'Re-usable', 'value': 'Re-usable'}, {'key': 'Analyze', 'value': 'Analyze'}, {'key': 'Assure', 'value': 'Assure'}, {'key': 'Integrate', 'value': 'Integrate'}, {'key': 'Plan', 'value': 'Plan'}, {'key': 'Describe', 'value': 'Describe'}, {'key': 'Discover', 'value': 'Discover'}, {'key': 'Collect', 'value': 'Collect'}, {'key': 'Describe / Metadata', 'value': 'Describe / Metadata'}, {'key': 'Preserve', 'value': 'Preserve'}, {'key': 'Local Data Management', 'value': 'Local Data Management'}, {'key': 'Responsible Data Use', 'value': 'Responsible Data Use'}, {'key': 'The Case for Data Stewardship', 'value': 'The Case for Data Stewardship'}, {'key': 'Data Management Plans', 'value': 'Data Management Plans'}, {'key': 'Publish/Share', 'value': 'Publish/Share'}, {'key': 'Acquire', 'value': 'Acquire'}, {'key': 'Process & Analyze', 'value': 'Process & Analyze'}]
                }
                template = temlate_doc('learningresources')
                for key in template:
                    if key in user_identifier:
                        return_json[key]={
                            "label": key.replace("_"," ").replace("."," ").title(),
                            "name": key,
                            "element": "select",
                            "options": [
                                {"key": "arXiv Author ID","value": "arXiv Author ID"},
                                {"key": "Google Scholar Profiles","value": "Google Scholar Profiles"},
                                {"key": "LinkedIn","value": "LinkedIn"},
                                {"key": "ORCID iD","value": "ORCID iD"},
                                {"key": "ResearcherID","value": "ResearcherID"},
                                    ]
                        }

                    if key in org_identifier:
                        return_json[key]={
                            "label": key.replace("_"," ").replace("."," ").title(),
                            "name": key,
                            "element": "select",
                            "options": [
                                {"key": "GRID","value": "GRID"},
                                {"key": "ISNI","value": "ISNI"},
                                {"key": "Ringgold","value": "Ringgold"},
                                {"key": "ROR","value": "ROR"},
                                    ]
                        }
                    if key in yes_no_unknown:
                        return_json[key]={
                            "label": key.replace("_"," ").replace("."," ").title(),
                            "name": key,
                            "element": "input",
                            "input_type":"checkbox",
                            "options": [{
                                    "key": "Yes",
                                    "value": "Yes",
                                    "checked":False
                                    },{
                                    "key": "No",
                                    "value": "No",
                                     "checked":True
                                    },{
                                    "key": "unknown",
                                    "value": "unknown",
                                     "checked":False
                                    }
                                    
                                    ]
                        }
                    if key in select_multiple_facet:
                        return_json[key]={
                        "label": key.replace("_"," ").replace("."," ").title(),
                        "element": "select",
                        "name":key,
                        "taxonomy":True,
                        "attributes": ["multiple"]
                        }
                    if key in taxonomy_field:
                        return_json[key]={
                        "label": key.replace("_"," ").replace("."," ").title(),
                        "name": key,
                        "element": "datalist",
                        "taxonomy":True
                        }

                    if key in taxonomy_select_single_field:
                        return_json[key]={
                        "label": key.replace("_"," ").replace("."," ").title(),
                        "name": key,
                        "element": "select",
                        "taxonomy":True
                    }

                    if key in textarea:
                        return_json[key]={
                        "label": key.replace("_"," ").replace("."," ").title(),
                        "name": key,
                        "element": "textarea"
                        }
                    if key in yn_select:
                        return_json[key]={
                            "label": key.replace("_"," ").replace("."," ").title(),
                            "name": key,
                            "element": "select",
                            "options": [{
                                    "key": "Yes",
                                    "value": True
                                    },
                                    {
                                    "key": "No",
                                    "value": False
                                    }]
                        }

                    if key in facet_checkbox:
                        return_json[key]={
                        "label":key.replace("_"," ").replace("."," ").title(),
                        "element": "input",
                        "facet":key,
                        "name":key,
                        "input_type":"checkbox"
                    }


                    if key in facet_datalist:
                        return_json[key]={
                        "label":key.replace("_"," ").replace("."," ").title(),
                        "element":"datalist",
                        "name":key,
                        "facet":key,
                        "taxonomy":False
                    }
                    if key in taxonomy_datalist:
                        return_json[key]={
                        "label":key.replace("_"," ").replace("."," ").title(),
                        "element":"datalist",
                        "name":key,
                     
                        "taxonomy":True
                    }


                    if key in flexdatalist:
                        return_json[key]={
                        "label":key.replace("_"," ").replace("."," ").title(),
                        "element":"flexdatalist",
                        "name":key,
                        "facet":key,
                        "taxonomy":False
                    }


                    if key in orgs:
                        return_json[key]={
                        "label":key.replace("_"," ").replace("."," ").title(),
                        "element":"datalist",
                        "name":key,
                 
                        "taxonomy":True
                    }


                    if key in select_single_taxonomy:
                        return_json[key]={
                        "label":key.replace("_"," ").replace("."," ").title(),
                        "element":"select",
                        "attributes": ["single"],
                        "name":key,
                        
                        "taxonomy":True
                        }

                    if key in select_multiple_taxonomy:
                        return_json[key]={
                        "label":key.replace("_"," ").replace("."," ").title(),
                        "element":"select",
                        "attributes": ["multiple"],
                        "name":key,
                        "taxonomy":True
                        }

                    if key in text:
                        return_json[key]={
                            "label": key.replace("_"," ").replace("."," ").title(),
                            "name": key,
                            "element": "input",
                            "input_type": "text"
                        }

                    if key in dates:
                        return_json[key]={
                            "label": key.replace("_"," ").replace("."," ").title(),
                            "name": key,
                            "element": "input",
                            "input_type": "date"
                        }

                    if key in email:
                        return_json[key]={
                            "label": key.replace("_"," ").replace("."," ").title(),
                            "name": key,
                            "element": "input",
                            "input_type": "email"
                        }
                    if key in url:
                        return_json[key]={
                            "label": key.replace("_"," ").replace("."," ").title(),
                            "name": key,
                            "element": "input",
                            "input_type": "url"
                        }
                for key in return_json:
                    if 'facet' in return_json[key]:
                        if 'input_type' in return_json[key]:
                            if return_json[key]['input_type']=='checkbox':
                                print('checkbox')
                                fac=return_json[key]['facet']
                                return_json[key]['options']=[]
                                for new_key in facet_json["facets"][fac]:
                                    return_json[key]['options'].append({"key": new_key, "value": new_key})
                        else:
                            fac=return_json[key]['facet']
                            return_json[key]['options']=[]
                            for new_key in facet_json["facets"][fac]:
                                return_json[key]['options'].append({"key": new_key, "value": new_key})
                    if 'taxonomy' in return_json[key]:
                        if return_json[key]['taxonomy']:
                            print(key)
                            print(taxonomy_keys)
                            vocab_name=taxonomy_keys[return_json[key]['name']]
                            print(vocab_name)
                            for result in  vocabularies_json['results']:
                                if result['name']==vocab_name:
                                    return_json[key]['options']=[]
                                    for value in result['values']:
                                        return_json[key]['options'].append({"key": value, "value": value})
                f = open('/opt/DMTClearinghouse/extras/countries.json', encoding='utf-8')
                countries=json.load(f)
                return_json["country_of_origin"]= {
                "label": "Country of Origin",
                "name": "country_of_origin",
                "element": "select",
                "attributes": [
                "single"
                ],
                "options":countries               
                }
                
                new_return_json={}
                for key in return_json:
                    if 'attributes' not in return_json[key]:
                        return_json[key]['attributes']=[]
                    if key in required_obj['Recommended']:
                        return_json[key]['required']='recommended'
                    elif key in required_obj['Optional']:
                        return_json[key]['required']='optional'
                    elif key in required_obj['Required']:
                        return_json[key]['required']='required'
                    else:
                        return_json[key]['required']='recommended'

                    if return_json[key]['name'] in custom_labels:
                        return_json[key]['label']=custom_labels[return_json[key]['name']]
                    
                    return_json[key]['name']=return_json[key]['name'].replace(".", "__")
                    key_general=True
                    for field_set_obj in field_sets:
                        if key in field_set_obj['contains']:
                            key_general=False
                            field_set_obj['fields'].append(return_json[key])
                    if key_general:
                        field_sets[0]['fields'].append(return_json[key])
                        field_sets[0]['contains'].append(key)

                        # print(r.json())
                       

                        
                #                add framework_nodes to fieldsets
                for obj in field_sets:
                    if obj['name']=='educational_information':
                        obj['framework_nodes']=framework_nodes
                #field_sets['framework_nodes']=framework_nodes

                response = app.response_class(
                response=json.dumps(field_sets),
                status=200,
                mimetype='application/json')
                return response
        if document is not None:
            print('not none')
            allowed_documents = ['documentation.html',
                                    'documentation.md', 'documentation.htm','template','metadata']
            if document not in allowed_documents:
                return render_template('bad_document.html', example="documentation.html"), 400
            elif document=='template':
                template = temlate_doc('learningresources')
                response = app.response_class(
                response=json.dumps(template),
                status=200,
                mimetype='application/json')
                return response
            elif document=='metadata':
                template = temlate_doc('learningresources')
                response = app.response_class(
                response=json.dumps(template),
                status=200,
                mimetype='application/json')
                return response
            else:
                this_docstring = learning_resource_post.__doc__ + \
                    json.dumps(temlate_doc('learningresources'))
                result1 = resources.search("*:*", rows=1)
                id = result1.docs[0]["id"]
                this_docstring = this_docstring.replace('IDPLACEHOLDER', id)
                return generate_documentation(this_docstring, document, request, True)
      





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
    ;;field:{"name":"facet_limit","type":"int","example":"15","description":"Maximum number of results to return. Default is 100. -1 shows all."}
    ;;field:{"name":"facet_sort","type":"string","example":"count","description":"Order of the facets can be \\\"count\\\" or \\\"index\\\". Index is Alphabetic"}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    ;;postjson:{"search": [{"group": "and","and": [{"field": "keywords","string": "ethics","type": "simple"},{"field": "created","string": "2019-05-20T17:33:18Z","type": "gte"} ],"or": [{"field": "submitter_name","string": "Karl","type": "simple"}]}],"limit": 10,"offset": 0, "sort":"id asc", "facet_limit":-1,"facet_sort":"count"}
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
        
        if current_user.is_authenticated:
            if "admin" in current_user.groups:
                searchstring = append_searchstring(searchstring, request, "pub_status")
            elif "editor" in current_user.groups:
                searchstring = append_searchstring(searchstring, request, "pub_status")
            elif "reviewer" in current_user.groups:
                searchstring = searchstring+" OR(pub_status:in-process OR pub_status:published  OR pub_status:in-review)"
                searchstring = append_searchstring(searchstring, request, "pub_status")
            elif "submitter" in current_user.groups:
                searchstring = searchstring+" OR(pub_status:in-process OR pub_status:published)"
                searchstring = append_searchstring(searchstring, request, "pub_status")
            else:
                searchstring = searchstring+" AND pub_status:published"

            if request.args.get("my_resources"):

                searchstring=searchstring+" AND creator:"+current_user.name
                
                
        elif request.args.get("api-key"):
                if request.args.get("api-key") in  app.config["API_KEYS"]:
                    searchstring = append_searchstring(searchstring, request, "pub_status")
                else:
                    searchstring = searchstring+" AND pub_status:published"
        else:
            searchstring = searchstring+" AND pub_status:published"


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
            searchstring, request, "contact.org")
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
        searchstring = append_searchstring(searchstring, request, "resource_modification_date")
        searchstring = append_searchstring(searchstring, request, "modification_date")
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
        if request.args.get("facet_limit"):
            params['facet.limit']=request.args.get("facet_limit") 
        if request.args.get("facet_sort"):
            params['facet.sort']=request.args.get("facet_sort") 

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
        if request.args.get('my_content'):
            current_user.id

        if current_user.is_authenticated:
            if "admin" in current_user.groups:
                searchstring = append_searchstring(searchstring, request, "pub_status")
            elif "editor" in current_user.groups:
                searchstring = append_searchstring(searchstring, request, "pub_status")
            elif "reviewer" in current_user.groups:
                searchstring = searchstring+" OR(pub_status:in-process OR pub_status:published  OR pub_status:in-review)"
                searchstring = append_searchstring(searchstring, request, "pub_status")
            elif "submitter" in current_user.groups:
                searchstring = searchstring+" OR(pub_status:in-process OR pub_status:published)"
                searchstring = append_searchstring(searchstring, request, "pub_status")
            else:
                searchstring = searchstring+" AND pub_status:published"
                
        else:
            searchstring = searchstring+" AND pub_status:published"
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

            if 'facet_limit' in content.keys():
                params['facet.limit']=content['facet_limit']

            if 'facet_sort' in content.keys():
                params['facet.sort']=content['facet_sort']
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

@app.route("/api", methods=['GET'])
@app.route("/api/", methods=['GET'])
def api():
    """ 
    GET:
        Shows available routes with links to documentation built dynamically.


    Returns: 
            HTML

    """
    rulelist = []
    not_protected=["/api/vocabularies/","/api/resources/","/api/feedback/","/api/schema/"]
    exclude_routes=["/api/login/","/api/logout/","/api/login_json","/api/logout_json","/api/orcid_sign_in","/api/protected","/api/passwordreset/","/api/user/groups","/api/orcid_sign_in/orcid_callback","/api/admin/urlcheck/","/api/admin/reindex/","/api/admin/tests/","/api/rss","/api/surveys/","/api/pub_status/"]
    print(app.url_map)
    for rule in app.url_map.iter_rules():
        print(rule)
        
        
        if "/api/" in rule.rule and rule.rule not in exclude_routes:
            if "<" not in rule.rule:
                if rule.rule != "/api/":
                    if rule.rule+"documentation.html" not in rulelist:
                        if rule.rule in not_protected:
                            if rule.rule+"documentation.html" not in rulelist:
                                rulelist.append(rule.rule+"documentation.html")
                        else:
                            if rule.rule+"documentation.html (protected)" not in rulelist:
                                rulelist.append(rule.rule+"documentation.html (protected)")
        
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
                if 'multiValued' in field:
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

@app.route("/api/admin/urlcheck/",  methods=['GET'])
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
            elif "editor" in current_user.groups:
                return render_template("edit_vocab.html")
            else:
                return{"status":"error","message":"Only admins and editors can edit vocabularies."},400
        else:
            return{"status":"error","message":"Only admins and editors can edit vocabularies."},400

    if document == "add":
        if current_user.is_authenticated:
            if "admin" in current_user.groups:
                return render_template("add_vocab.html")
            if "editor" in current_user.groups:
                return render_template("add_vocab.html")
            else:
                return{"status":"error","message":"Only admins and editors can add vocabularies."},400
        else:
            return{"status":"error","message":"Only admins and editors can add vocabularies."},400

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
            if 'editor' in current_user.groups or 'admin' in current_user.groups:
                if request.is_json:
                    vocabjson  = request.get_json()
                    #check if it has id,name, and values
                    if all(key in vocabjson for key in ("name","values", "id")):
                        if vocabjson['id'] and vocabjson['name'] and vocabjson['values']:
                            #clean it up:
                            if "type" in vocabjson:
                                vocabtype=vocabjson['type']
                            else:
                                vocabtype=""
                            newvocabjson={'id':vocabjson['id'],'name':vocabjson['name'],'values':vocabjson['values'],'type':vocabtype}
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
                return{"status":"error","message":"Only admins and editors can modify vocabularies."},400
        else:
            return{"status":"error","message":"You must be logged in"},400

@app.route("/api/login_json", methods=['POST'])
def login_json():
    """ 
    POST:
        Validates credentials of users and creates and stores a session.
        Form Request: 

            username (string):  The users username.
            password (string):  The users password.
        Returns: 
            cookie:session token
            json:message
    """

    if request.method == 'POST':
        r_obj=request.get_json()
        print()
        user_object = get_user(r_obj['username'])
        if user_object:
            computed = user_object['hash']
            passwd = r_obj['password']
            if drash.verify(passwd, computed):
                login_user(User(user_object['id'], user_object['groups'], user_object['name']))
                resp = make_response({'status':'success','message':'Good login'});
                return resp

        return {'status':'error','message':'Bad login'}




@app.route("/api/login/", methods=['GET','POST'])
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

@app.route("/api/logout_json")
@login_required
def logout_json():
    logout_user()
    return {"message":"Logged out"}

@app.route("/api/logout/")
@login_required
def logout():
    try:
        logout_user()
        return {'status':'success'}
    except:
        return {'status':'fail'}


@app.route('/api/protected')
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


@app.route("/api/passwordreset/", methods=['GET','POST'])
def passwordreset():
    yesterday=datetime.now() - timedelta(days=1)
    if request.method == 'GET':
        
        if request.args.get('token'):
            token = request.args.get('token')
            tokentuple=db.session.query(Tokens.token).filter(Tokens.token == token).filter(Tokens.date>=yesterday).first()
            if tokentuple:
                return render_template("password_reset.html",token=token,url="https://"+request.host+"/api/passwordreset/")
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
                        db.session.delete(ttd)
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



@app.route("/api/user/groups", methods=['GET'])

def user_groups():
    print(current_user.__dict__)
    if current_user.is_authenticated:
        jsonobj=current_user.__dict__
    else:
        jsonobj={'id':None,'groups':[],'name':None}
    return jsonobj


@app.route("/api/user/<action>", methods=['GET','POST'])
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
                if action=="users.json":

                    sorteduserjson = sorted(userjson, key=lambda k: k['name'].lower())
                    return_json={"users":sorteduserjson}
                    r = make_response( return_json )
                    r.mimetype = 'application/json'
                    return r     

 
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
                                resetlink='''https://'''+request.host+"/api/passwordreset/?token="+token
                                servername='''https://'''+request.host
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
    return("API")
@app.route("/api/static/<path:path>")
def send_static(path):
    return send_from_file('static', path)


orcid_client_id = app.config["ORCID_CLIENT_ID"]
orcid_client_secret = app.config["ORCID_CLIENT_SECRET"]
orcid_discovery_url = app.config["ORCID_AUTH_URL"]
orcid_exchange_url = app.config["ORCID_EXCHANGE_URL"]
orcid_redirect_url = app.config["ORCID_REDIRECT_URL"]
front_end_url = app.config["FRONT_END_URL"]
orcid_client = WebApplicationClient(orcid_client_id)

@app.route("/api/orcid_sign_in", methods = ["GET", "POST"])
def orcid_sign_in():
    request_uri = orcid_client.prepare_request_uri(
        orcid_discovery_url,
        redirect_uri= orcid_redirect_url,
        scope="openid",  #use "openid" or "/authenticate"
    )
    return redirect(request_uri)

@app.route("/api/orcid_sign_in/orcid_callback", methods = ["GET", "POST"])
def orcid_callback():
    request.url=request.url.replace(request.host_url,front_end_url)
    request.base_url=request.base_url.replace(request.host_url,front_end_url)
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
