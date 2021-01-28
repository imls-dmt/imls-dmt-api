
print("Loading modules...")
import json
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, JSON, Float, Boolean
import drupal_config
import datetime
import requests
import pysolr
import os
import uuid

date=0
file=""
os.system('terminus auth:login --machine-token='+drupal_config.machine_token)
stream = os.popen('terminus backup:list esip-multisite.live --format json')
output = stream.read()
backupjson=json.loads(output)
for key in backupjson.keys():
        if key.endswith("automated_database"):
                if backupjson[key]['date']>date:
                        date=backupjson[key]['date']
                        file=backupjson[key]['file']
file_with_no_gz=os.path.splitext("/nightly-backups/"+file)[0]
if os.path.isfile(file_with_no_gz):
    print("We are up to date")
else:
    stream = os.popen("terminus backup:get --file "+file+" esip-multisite.live")
    url = stream.read()
    print(url)
    r = requests.get(url, allow_redirects=True)
    open('/nightly-backups/'+file, 'wb').write(r.content)
    os.system('gunzip /nightly-backups/'+file)
    os.system('mysql imls_nightly < '+file_with_no_gz)






print("Deleting and creating indexes")
os.system('sudo su - solr -c "/opt/solr/bin/solr delete -c learningresources"')
os.system('sudo su - solr -c "/opt/solr/bin/solr create -c learningresources -n data_driven_schema_configs"')


os.system('sudo su - solr -c "/opt/solr/bin/solr delete -c users"')
os.system('sudo su - solr -c "/opt/solr/bin/solr create -c users -n data_driven_schema_configs"')
os.system('sudo su - solr -c "/opt/solr/bin/solr delete -c taxonomies"')
os.system('sudo su - solr -c "/opt/solr/bin/solr create -c taxonomies -n data_driven_schema_configs"')
os.system('sudo su - solr -c "/opt/solr/bin/solr delete -c timestamps"')
os.system('sudo su - solr -c "/opt/solr/bin/solr create -c timestamps -n data_driven_schema_configs"')
os.system('sudo su - solr -c "/opt/solr/bin/solr delete -c feedback"')
os.system('sudo su - solr -c "/opt/solr/bin/solr create -c feedback -n data_driven_schema_configs"')
r=requests.get("http://localhost:8983/solr/users/update?commit=true")

print("Add Learning Resources fields")
fields= ['{"add-field": {"name":"title", "type":"text_general", "multiValued":false, "required":true, "stored":true ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"url", "type":"text_general", "multiValued":false, "required":true, "stored":true ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"access_cost", "type":"boolean", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"submitter_name", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"submitter_email", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"author_names", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"author_org.name", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"author_org.name_identifier", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"author_org.name_identifier_type", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
'{"add-field": {"name":"authors.familyName", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
'{"add-field": {"name":"authors.givenName", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
'{"add-field": {"name":"authors.name_identifier", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
'{"add-field": {"name":"authors.name_identifier_type", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
'{"add-field": {"name":"contact.email", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
'{"add-field": {"name":"contact.name", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
'{"add-field": {"name":"contact.org", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"subject", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"keywords", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"license", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"usage_info", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"citation", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"publisher", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"version", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"created", "type":"pdate", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"published", "type":"pdate", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"ed_frameworks.name", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"ed_frameworks.nodes.name", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"ed_frameworks.nodes.description", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"language_primary", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"languages_secondary", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"target_audience", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"purpose", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"completion_time", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"media_type", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"lr_type", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"contributors.givenName", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"contributors.familyName", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"contributors.type", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"status", "type":"boolean", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"abstract_data", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"abstract_format", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"locator_data", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"locator_type", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"country_of_origin", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"credential_status", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"modification_date", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"name_identifier", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"name_identifier_type", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"accessibility_features.name", "type":"text_general", "multiValued":true, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"accessibility_summary", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"ratings", "type":"pfloat", "multiValued":true, "stored":true,"required":false ,"indexed":false}}',
 '{"add-field": {"name":"rating", "type":"pfloat", "multiValued":false, "stored":true,"required":false ,"indexed":false}}',
 '{"add-field": {"name":"creator", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"md_record_id", "type":"text_general", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',]


facet_fields=[
 '{"add-field": {"name":"facet_author_names", "type":"string", "multiValued":true, "stored":true,"required":false ,"indexed":true}}',  
 '{"add-field": {"name":"facet_author_org.name", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_subject", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_keywords", "type":"string", "multiValued":true, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_license", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_usage_info", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_publisher", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_accessibility_features.name", "type":"string", "multiValued":true, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_language_primary", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_languages_secondary", "type":"string", "multiValued":true, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_ed_frameworks.name", "type":"string", "multiValued":true, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_target_audience", "type":"string", "multiValued":true, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_lr_type", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_purpose", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_media_type", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true}}',
 '{"add-field": {"name":"facet_access_cost", "type":"boolean", "multiValued":false, "stored":true,"required":false ,"indexed":true}}']

timestamp_fields=[
 '{"add-field": {"name":"ip", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"type", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"timestamp", "type":"pdate", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"userid", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"resourceid", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}'
 ]

feedback_fields=[
 '{"add-field": {"name":"ip", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"feedback", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"rating", "type":"pfloat", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"timestamp", "type":"pdate", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"email", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}',
 '{"add-field": {"name":"resourceid", "type":"string", "multiValued":false, "stored":true,"required":false ,"indexed":true,"default":""}}'
 ]

for field in feedback_fields:
    j=json.loads(field)
    # print(j)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    url="http://localhost:8983/solr/feedback/schema"
    r = requests.post(url, data=json.dumps(j), headers=headers)
    if r.status_code!=200:
        print(r.json())
        print(r.text)

for field in timestamp_fields:
    j=json.loads(field)
    # print(j)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    url="http://localhost:8983/solr/timestamps/schema"
    r = requests.post(url, data=json.dumps(j), headers=headers)
    if r.status_code!=200:
        print(r.json())
        print(r.text)

for field in fields:
    j=json.loads(field)
    # print(j)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    url="http://localhost:8983/solr/learningresources/schema"
    r = requests.post(url, data=json.dumps(j), headers=headers)
    if r.status_code!=200:
        print(r.json())
        print(r.text)


for field in facet_fields:
    j=json.loads(field)
    # print(j)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    url="http://localhost:8983/solr/learningresources/schema"
    r = requests.post(url, data=json.dumps(j), headers=headers)
    if r.status_code!=200:
        print(r.json())
        print(r.text)



print("Add user fields")
fields= ['{"add-field": {"name":"hash", "type":"text_general", "multiValued":false, "stored":true,"required":true}}',
 '{"add-field": {"name":"name", "type":"string", "multiValued":false, "stored":true,"required":true}}',
 '{"add-field": {"name":"email", "type":"text_general", "multiValued":false, "stored":true,"required":false}}',
 '{"add-field": {"name":"timezone", "type":"text_general", "multiValued":false, "stored":true,"required":false}}',
 '{"add-field": {"name":"groups", "type":"text_general", "multiValued":true, "stored":true,"required":false}}',
 '{"add-field": {"name":"enabled", "type":"boolean", "multiValued":false, "stored":true,"required":false}}']
for field in fields:
    j=json.loads(field)
    # print(j)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    url="http://localhost:8983/solr/users/schema"
    r = requests.post(url, data=json.dumps(j), headers=headers)
    if r.status_code!=200:
        print(r.json())
        print(r.text)


print("Add taxonomies fields")
fields= ['{"add-field": {"name":"name", "type":"string", "multiValued":false, "stored":true,"required":true}}',
 '{"add-field": {"name":"values", "type":"text_general", "multiValued":true, "stored":true,"required":false}}']
for field in fields:
    j=json.loads(field)
    # print(j)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    url="http://localhost:8983/solr/taxonomies/schema"
    r = requests.post(url, data=json.dumps(j), headers=headers)
    if r.status_code!=200:
        print(r.json())
        print(r.text)

userssolr = pysolr.Solr('http://localhost:8983/solr/users/', timeout=10)

usernames=[]
print("Building DB classes...")
Base = automap_base()
engine = create_engine(drupal_config.connectstring)
Base.prepare(engine, reflect=True)
Nodes = Base.classes.node
Users =Base.classes.users
UsersRoles = Base.classes.users_roles
LRUrls =Base.classes.field_data_field_lr_url
Payment=Base.classes.field_data_field_lr_payment_required
Submitter=Base.classes.field_data_field_dmt_submitter_name
SubmitterEmail=Base.classes.field_data_field_submission_contact_email_a
Authorid=Base.classes.field_data_field_lr_author_people
PeopleFirst=Base.classes.field_data_field_lr_ppl_name_first
PeopleLast=Base.classes.field_data_field_lr_ppl_name_last
AuthorOrg=Base.classes.field_revision_field_lr_author_organizations
TaxonomyTerms=Base.classes.taxonomy_term_data
LongName=Base.classes.field_data_field_long_name
Contact=Base.classes.field_data_field_lr_contact_people
ContactAuthorOrg=Base.classes.field_revision_field_lr_contact_organizations
ContributorPeople= Base.classes.field_revision_field_lr_contributor_people
ContributorPerson=Base.classes.field_data_field_lr_contributor_person
ContributorType=Base.classes.field_revision_field_lr_contributor_type
ContribOrgs=Base.classes.field_revision_field_lr_contributor_orgs
ContribOrg=Base.classes.field_revision_field_lr_contributor_org
Abstracts=Base.classes.field_data_field_lr_abstract
Subjects=Base.classes.field_data_field_lr_subject
Keywords=Base.classes.field_data_field_lr_keywords
Licenses=Base.classes.field_data_field_lr_license
UsageRights=Base.classes.field_data_field_lr_usage_rights
Citation=Base.classes.field_data_field_lr_citation
Locator=Base.classes.field_data_field_lr_locator_id
LocatorType=Base.classes.field_data_field_lr_locator_type
Publisher=Base.classes.field_data_field_lr_publisher
Version=Base.classes.field_data_field_lr_version
DateCreated =Base.classes.field_data_field_lr_date_created
DatePublished =Base.classes.field_data_field_lr_date_published
AccessFeatures =Base.classes.field_data_field_lr_access_features
LanguagePrimary = Base.classes.field_data_field_lr_language_primary
LanguagesSecondary=Base.classes.field_data_field_lr_languages_secondary
EdFramework=Base.classes.field_data_field_lr_ed_framework;
EdFrameworkD1=Base.classes.field_data_field_lr_ed_framework_node_data1
EdFrameworkFair=Base.classes.field_data_field_framework_node_fair
EdFrameworkEsip=Base.classes.field_data_field_lr_ed_framework_node_esip
EdFrameworkUsgs=Base.classes.field_data_field_lr_ed_framework_node_usgs
EdAudience=Base.classes.field_data_field_lr_ed_audience
Purpose=Base.classes.field_data_field_lr_ed_purpose
CompletionTime=Base.classes.field_data_field_lr_completion_time
MediaType=Base.classes.field_data_field_lr_media_type
LearningResourceType=Base.classes.field_data_field_lr_type
print("Creating db session...")
session = Session(engine)

print("Creating new session")

# Pull drupal_config info from file

NewEngine = create_engine(drupal_config.newconnectstring)
NewBase = automap_base()
NewBase.prepare(NewEngine, reflect=True)
Learningresources = NewBase.classes.learningresources
NewUsers = NewBase.classes.users
Taxonomies = NewBase.classes.taxonomies
NewSession = Session(NewEngine)

def get_controlled_vocabulary(vid):
    returnarray=[]
    items=session.query(TaxonomyTerms.name).filter(TaxonomyTerms.vid==vid).group_by(TaxonomyTerms.name).all()
    for item in items:
        returnarray.append(item[0])
    return returnarray
def get_names(id):
    return_object={"familyName": "","givenName": ""}
    firstnamez=session.query(PeopleFirst.field_lr_ppl_name_first_value).filter(PeopleFirst.entity_id==id).first()
    if firstnamez is not None:
        return_object['givenName']=firstnamez[0]
    lastnamez=session.query(PeopleLast.field_lr_ppl_name_last_value).filter(PeopleLast.entity_id==id).first()
    if lastnamez is not None:
        return_object['familyName']=lastnamez[0]
    return return_object


def get_taxonomy_value(id):
        namedata=session.query(TaxonomyTerms.name).filter(TaxonomyTerms.tid==id).first()
        if namedata is not None:
            return namedata[0]
        else:
            return ""

def get_value(field,table):
    value=session.query(field).filter(table.entity_id==lr.nid).first()
    if value is not None:
        return value[0]
    else:
        return ""


def get_date(field,table):
    value=session.query(field).filter(table.entity_id==lr.nid).first()
    if value is not None:
        return value[0].strftime('%Y-%m-%dT%H:%M:%SZ')
    else:
        return ""


def get_values(field,table):
    returnarray=[]
    values=session.query(field).filter(table.entity_id==lr.nid).all()
    if values is not None:
        for value in values:
            returnarray.append(value[0])
    return returnarray


def get_name_from_target(field,table):
    id=session.query(field).filter(table.entity_id==lr.nid).first()
    if id is not None:
        return get_names(id[0])
    else:
        return {"lastname": "","firstname": ""}

def get_first_names_from_target(field,table):
    namesarray=[]
    ids=session.query(field).filter(table.entity_id==lr.nid).all()
    if ids is not None:
      for id in ids:
         namesarray.append(get_names(id[0])["firstname"])
      return namesarray
    else:
        return []
def get_last_names_from_target(field,table):
    namesarray=[]
    ids=session.query(field).filter(table.entity_id==lr.nid).all()
    if ids is not None:
      for id in ids:
         namesarray.append(get_names(id[0])["lastname"])
      return namesarray
    else:
        return []

def get_value_from_target(field,table):
    id=session.query(field).filter(table.entity_id==lr.nid).first()
    if id is not None:
        return get_taxonomy_value(id[0])
    else:
        return ""


def get_values_from_target(field,table):
    ids=session.query(field).filter(table.entity_id==lr.nid).all()
    returnarray=[]
    if ids is not None:
        for id in ids:
            returnarray.append(get_taxonomy_value(id[0]))
    return returnarray

def get_author(uid):
    name=session.query(Users.name).filter(Users.uid==uid).first()
    if name is not None:
        if name[0] not in usernames:
            usernames.append(name[0])
        return name[0]
    else:
        return ""

def build_authors(field,table):
    namesarray=[]
    ids=session.query(field).filter(table.entity_id==lr.nid).all()
    if ids is not None:
      for id in ids:
         namesarray.append({"givenName":get_names(id[0])["givenName"],"familyName":get_names(id[0])["familyName"],"name_identifier":"","name_identifier_type":""})
      return namesarray
    else:
        return []
def build_author_names(field,table):
    namesarray=[]
    ids=session.query(field).filter(table.entity_id==lr.nid).all()
    if ids is not None:
      for id in ids: 
         namesarray.append(get_names(id[0])["givenName"].strip()+" "+get_names(id[0])["familyName"].strip())
      return namesarray
    else:
        return []


def build_accessibility_features(field,table):
    ids=session.query(field).filter(table.entity_id==lr.nid).all()
    returnarray=[]
    if ids is not None:
        for id in ids:
            returnarray.append({"name":get_taxonomy_value(id[0])})
    return returnarray

def build_frameworks(field,table):
   returnarray=[]
   frameworks=get_values_from_target(EdFramework.field_lr_ed_framework_target_id,EdFramework)
   for framework in frameworks:
      if framework=="DataONE Education Modules":
         obj={"name":framework,"nodes":[]}
         nodes=get_values_from_target(EdFrameworkD1.field_lr_ed_framework_node_data1_target_id,EdFrameworkD1)
         for node in nodes:
            obj["nodes"].append({"description":"","name":node})
         returnarray.append(obj)
      elif framework=="FAIR Data Principles":
         obj={"name":framework,"nodes":[]}
         nodes=get_values_from_target(EdFrameworkFair.field_framework_node_fair_target_id,EdFrameworkFair)
         for node in nodes:
            obj["nodes"].append({"description":"","name":node})
         returnarray.append(obj)
      elif framework=="ESIP Data Management for Scientists Short Course":
         obj={"name":framework,"nodes":[]}
         nodes=get_values_from_target(EdFrameworkEsip.field_lr_ed_framework_node_esip_target_id ,EdFrameworkEsip)
         for node in nodes:
            obj["nodes"].append({"description":"","name":node})
         returnarray.append(obj)
      elif framework=="USGS Science Support Framework":
         obj={"name":framework,"nodes":[]}
         nodes=get_values_from_target(EdFrameworkUsgs.field_lr_ed_framework_node_usgs_target_id,EdFrameworkUsgs)
         for node in nodes:
            obj["nodes"].append({"description":"","name":node})
         returnarray.append(obj)
      else:
         obj={"name":framework,"nodes":[]}
         returnarray.append(obj)
   return returnarray

def object_as_dict(obj):
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}

#TODO implement the controlled vocabularies below.

def insert_taxonomies(array,name):
    taxonomiessolr = pysolr.Solr('http://localhost:8983/solr/taxonomies/', timeout=10)
    j=json.loads('{"name":"'+name+'"}')
    j['values']=array
    taxonomiessolr.add([j])
    r=requests.get("http://localhost:8983/solr/taxonomies/update?commit=true")
    if r.status_code!=200:
        print(r.json())
        print(r.text)

DMTAccessibilityFeatures=get_controlled_vocabulary(28)
insert_taxonomies(DMTAccessibilityFeatures,"Accessibility Features")
DMTCompletionTimeframes=get_controlled_vocabulary(29)
insert_taxonomies(DMTCompletionTimeframes,"Completion Timeframes")
DMTContributorTypes=get_controlled_vocabulary(30)
insert_taxonomies(DMTContributorTypes,"Contributor Types")
DMTEducationalAudiences=get_controlled_vocabulary(31)
insert_taxonomies(DMTEducationalAudiences,"Educational Audiences")
DMTEducationalFrameworkNodes_DataONE=get_controlled_vocabulary(32)
insert_taxonomies(DMTEducationalFrameworkNodes_DataONE,"Educational Framework Nodes DataONE")
DMTEducationalFrameworkNodes_ESIPDataManagementforScientistsShortCourse=get_controlled_vocabulary(33)
insert_taxonomies(DMTEducationalFrameworkNodes_ESIPDataManagementforScientistsShortCourse,"Educational Framework Nodes ESIP Data Management for Scientists Short Course")
DMTEducationalFrameworkNodes_USGS=get_controlled_vocabulary(34)
insert_taxonomies(DMTEducationalFrameworkNodes_USGS,"Educational Framework Nodes USGS")
DMTEducationalFrameworks=get_controlled_vocabulary(35)
insert_taxonomies(DMTEducationalFrameworks,"Educational Frameworks")
DMTEducationalPurpose=get_controlled_vocabulary(36)
insert_taxonomies(DMTEducationalPurpose,"Educational Purpose")
DMTEducationalRoles=get_controlled_vocabulary(37)
insert_taxonomies(DMTEducationalRoles,"Educational Roles")
DMTKeywords=get_controlled_vocabulary(38)
insert_taxonomies(DMTKeywords,"Keywords")
DMTLicenses=get_controlled_vocabulary(39)
insert_taxonomies(DMTLicenses,"Licenses")
DMTLocatorTypes=get_controlled_vocabulary(40)
insert_taxonomies(DMTLocatorTypes,"Locator Types")
DMTLearningResourceTypes=get_controlled_vocabulary(41)
insert_taxonomies(DMTLearningResourceTypes,"Learning Resource Types")
DMTMediaType=get_controlled_vocabulary(42)
insert_taxonomies(DMTMediaType,"Media Type")
DMTOrganizations=get_controlled_vocabulary(43)
insert_taxonomies(DMTOrganizations,"Organizations")
DMTPeople=get_controlled_vocabulary(44)
insert_taxonomies(DMTPeople,"People")
DMTSubjectDisciplines=get_controlled_vocabulary(45)
insert_taxonomies(DMTSubjectDisciplines,"Subject Disciplines")
DMTUsageRights=get_controlled_vocabulary(46)
insert_taxonomies(DMTUsageRights,"Usage Info")
DMTEducationalFrameworkNodes_FAIRDataPrinciples=get_controlled_vocabulary(47)
insert_taxonomies(DMTEducationalFrameworkNodes_FAIRDataPrinciples,"Educational Framework Nodes FAIR Data Principles")
DMTEducationalFrameworkNodes_Test=get_controlled_vocabulary(48)
insert_taxonomies(DMTEducationalFrameworkNodes_Test,"Educational Framework Nodes Test")
#print(DMTAccessibilityFeatures)



NewSession.execute('''TRUNCATE TABLE learningresources''')
NewSession.commit()

#Migrate learning resources from SQL to SOLR
print("Migrating all learning resources...")
Learning_Resources=session.query(Nodes.title,Nodes.status,Nodes.nid,Nodes.uid,Nodes.created).filter(Nodes.type=='dmt_learning_resource').all()
jsondict=json.loads('{ "learning_resources":[]}')

for lr in Learning_Resources:
    j=json.loads('{}')
    j['title']=lr.title
    j['status']=lr.status
    j['url']=get_value(LRUrls.field_lr_url_url,LRUrls)
    j['access_cost']=get_value(Payment.field_lr_payment_required_value,Payment)
    j['facet_access_cost']=get_value(Payment.field_lr_payment_required_value,Payment)
    j['submitter_name']=get_value(Submitter.field_dmt_submitter_name_value,Submitter)
    j['submitter_email']=get_value(SubmitterEmail.field_submission_contact_email_a_email,SubmitterEmail)
    j['authors']=build_authors(Authorid.field_lr_author_people_target_id,Authorid)
    j['author_names']=build_author_names(Authorid.field_lr_author_people_target_id,Authorid)
    j['facet_author_names']=build_author_names(Authorid.field_lr_author_people_target_id,Authorid)
    j['author_org']={"name":get_value_from_target(AuthorOrg.field_lr_author_organizations_target_id,AuthorOrg),"name_identifier":"","name_identifier_type":""}
    j['facet_author_org']={"name":get_value_from_target(AuthorOrg.field_lr_author_organizations_target_id,AuthorOrg)}
    contact_name=get_value_from_target(Contact.field_lr_contact_people_target_id,Contact)
    contact_org=get_value_from_target(ContactAuthorOrg.field_lr_contact_organizations_target_id,ContactAuthorOrg)
    j['contact']={"name":contact_name,"org": contact_org,"email":""}
    j['abstract_data']=get_value(Abstracts.field_lr_abstract_value,Abstracts)
    j['abstract_format']=get_value(Abstracts.field_lr_abstract_format,Abstracts)
    j['subject']=get_value_from_target(Subjects.field_lr_subject_target_id,Subjects)
    j['facet_subject']=get_value_from_target(Subjects.field_lr_subject_target_id,Subjects)
    j['keywords']=get_values_from_target(Keywords.field_lr_keywords_target_id,Keywords)
    j['facet_keywords']=get_values_from_target(Keywords.field_lr_keywords_target_id,Keywords)
    j['license']=get_value_from_target(Licenses.field_lr_license_target_id,Licenses)
    j['facet_license']=get_value_from_target(Licenses.field_lr_license_target_id,Licenses)
    j['usage_info']=get_value_from_target(UsageRights.field_lr_usage_rights_target_id,UsageRights)
    j['facet_usage_info']=get_value_from_target(UsageRights.field_lr_usage_rights_target_id,UsageRights)
    j['citation']=get_value(Citation.field_lr_citation_value,Citation)
    j['locator_data']=get_value(Locator.field_lr_locator_id_value,Locator)
    j['locator_type']=get_value_from_target(LocatorType.field_lr_locator_type_target_id,LocatorType)
    j['publisher']=get_value_from_target(Publisher.field_lr_publisher_target_id,Publisher)
    j['facet_publisher']=get_value_from_target(Publisher.field_lr_publisher_target_id,Publisher)
    j['version']=get_value(Version.field_lr_version_value,Version)
    j['created']=get_date(DateCreated.field_lr_date_created_value,DateCreated)
    j['published']=get_date(DatePublished.field_lr_date_published_value,DatePublished)
    accessibility_features=build_accessibility_features(AccessFeatures.field_lr_access_features_target_id,AccessFeatures)
    j['accessibility_features']=accessibility_features
    j['facet_accessibility_features']=accessibility_features
    j['accessibility_summary']=""
    j['facet_language_primary']=get_value(LanguagePrimary.field_lr_language_primary_value,LanguagePrimary)
    j['language_primary']=get_value(LanguagePrimary.field_lr_language_primary_value,LanguagePrimary)
    j['languages_secondary']=get_values(LanguagesSecondary.field_lr_languages_secondary_value,LanguagesSecondary)
    j['facet_languages_secondary']=get_values(LanguagesSecondary.field_lr_languages_secondary_value,LanguagesSecondary)
    j['ed_frameworks']=build_frameworks(EdFramework.field_lr_ed_framework_target_id,EdFramework)
    j['facet_ed_frameworks']=build_frameworks(EdFramework.field_lr_ed_framework_target_id,EdFramework)
    j['target_audience']=get_values_from_target(EdAudience.field_lr_ed_audience_target_id,EdAudience)
    j['facet_target_audience']=get_values_from_target(EdAudience.field_lr_ed_audience_target_id,EdAudience)
    j['purpose']=get_value_from_target(Purpose.field_lr_ed_purpose_target_id,Purpose)
    j['facet_purpose']=get_value_from_target(Purpose.field_lr_ed_purpose_target_id,Purpose)
    j['completion_time']=get_value_from_target(CompletionTime.field_lr_completion_time_target_id,CompletionTime)
    j['media_type']=get_value_from_target(MediaType.field_lr_media_type_target_id,MediaType)
    j['facet_media_type']=get_value_from_target(MediaType.field_lr_media_type_target_id,MediaType)
    j['lr_type']=get_value_from_target(LearningResourceType.field_lr_type_target_id,LearningResourceType)
    j['facet_type']=get_value_from_target(LearningResourceType.field_lr_type_target_id,LearningResourceType)
    j['creator']=get_author(lr.uid)
    j['created']=datetime.datetime.fromtimestamp(lr.created).isoformat()
    j['md_record_id']=""
    j['ratings']=[]
    j['rating']=0
    nidstring=str(lr.nid)
    j['id']=str(uuid.uuid3(uuid.NAMESPACE_OID, nidstring))
    
    contributors=[]
    for contributorid in get_values(ContributorPeople.field_lr_contributor_people_value,ContributorPeople):
            contributorpersonid=session.query(ContributorPerson.field_lr_contributor_person_target_id).filter(ContributorPerson.entity_id==contributorid).first()
            if contributorpersonid is not None:
                contributorsnames=get_names(contributorpersonid[0])
            contributortype=""
            contributortypeid=session.query(ContributorType.field_lr_contributor_type_target_id).filter(ContributorType.entity_id==contributorid).first()
            if contributortypeid is not None:
                contributortype=get_taxonomy_value(contributortypeid[0])
            contributorsnames.update({'type':contributortype})
            contributors.append(contributorsnames)
    j['contributors']=contributors
    contributororgsvals=session.query(ContribOrgs.field_lr_contributor_orgs_value).filter(ContribOrgs.entity_id==lr.nid).all()
    j['contributor_orgs']=[]
    if contributororgsvals is not None:
        contributortype=""
        for contributororgsval in contributororgsvals:
            contributorobj={"name":"","type":""}
            contributororg=""
            contributortype=""
            contributorpersonid=session.query(ContribOrg.field_lr_contributor_org_target_id).filter(ContribOrg.entity_id==contributororgsval[0]).first()
            if contributorpersonid is not None:
                contributororg=get_taxonomy_value(contributorpersonid[0])
                contributorobj['name']=contributororg
            contributortypeid=session.query(ContributorType.field_lr_contributor_type_target_id).filter(ContributorType.entity_id==contributororgsval[0]).first()
            if contributortypeid is not None:
                contributortype=get_taxonomy_value(contributortypeid[0])
                contributorobj['type']=contributortype
            j['contributor_orgs'].append(contributorobj)

    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    url="http://localhost:8983/solr/learningresources/update/json/docs"
    r = requests.post(url, data=json.dumps(j), headers=headers)
    if r.status_code!=200:
        print(json.dumps(j))
        print(r.json())
        print(r.text)
    NewSession.add(Learningresources(id = j['id'], value=json.dumps(j)))
    jsondict['learning_resources'].append(j)

print("commiting")
NewSession.commit()
url="http://localhost:8983/solr/learningresources/update?commit=true"
r = requests.get(url)

#Get users that are members of groups that we are interested in migrating.
usertuple=session.query(Users)\
    .filter(Users.access!=0)\
    .filter(Users.status==1)\
    .filter(UsersRoles.uid==Users.uid)\
    .filter((UsersRoles.rid == 14) | (UsersRoles.rid == 15) |(UsersRoles.rid == 16) |(UsersRoles.rid == 17)  )\
    .distinct()
#Create each user and add them to the same groups on the destination.
for user in usertuple:
    userobj={}
    userobj['hash']=user.__dict__['pass']
    userobj['name']=user.name
    userobj['email']=user.mail
    userobj['timezone']=user.timezone
    userobj['groups']=[]
    userobj['enabled']=True
    userobj['groups'].append('lauth')
    userrolestuple=session.query(UsersRoles.rid)\
    .filter(Users.uid==user.uid)\
    .filter(Users.access!=0)\
    .filter(Users.status==1)\
    .filter(UsersRoles.uid==Users.uid)\
    .filter((UsersRoles.rid == 14) | (UsersRoles.rid == 15) |(UsersRoles.rid == 16) |(UsersRoles.rid == 17)  )\
    .distinct()
    for role in userrolestuple:
        for roleID in role:
            
                if roleID==14:  
                    userobj['groups'].append('admin')
                if roleID==15:  
                    userobj['groups'].append('editor')
                if roleID==16:  
                    userobj['groups'].append('reviewer')
                if roleID==17:  
                    userobj['groups'].append('submitter')
            
    userjson=json.loads(json.dumps(userobj))
    userssolr.add([userjson])
#Commit these actions.
r=requests.get("http://localhost:8983/solr/users/update?commit=true")

print("Done")
