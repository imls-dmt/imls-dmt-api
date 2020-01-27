from flask import Flask, request, redirect, url_for, render_template, make_response
import pysolr
import json
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import drupal_hash_utility
from docstring_parser import parse


#Create flask app
app = Flask(__name__)

#Pull config info from file
app.config.from_object('dmtconfig.DevConfig')

#Create a pysolr object for accessing the "learningresources" and "users" index
resources = pysolr.Solr(app.config["SOLR_ADDRESS"]+"learningresources/", timeout=10)
users = pysolr.Solr(app.config["SOLR_ADDRESS"]+"users/", timeout=10)
taxonomies = pysolr.Solr(app.config["SOLR_ADDRESS"]+"taxonomies/", timeout=10)
#flask_login implementation. 
login_manager = LoginManager()
login_manager.init_app(app)

#Drupal hash utility as we will continue to use Drupal hashes.
drash = drupal_hash_utility.DrupalHashUtility()


##############################
#Shared Functions and classes#
##############################
def append_searchstring(searchstring,request,name):
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
    def __init__(self,id,groups,name):
        self.id = id
        self.groups = groups
        self.name = name


#Callback for login_user
@login_manager.user_loader
def load_user(user_id):
    """ 
    Function used as a callback when login_user is called.
    Parameters: 

    user_id (UUID): ID of user.

    Returns:
        User object or None
    """
    userobj=users.search("id:\""+user_id+"\"", rows=1)
    for user in userobj:
        user.pop('_version_', None)
        user.pop('hash', None)
        return User(user['id'],user['groups'],user['name'])
    return None


#internal user with hash
def get_user(user_name):
    """
    Internal function for building a user object with hash from a given username.
    Parameters: 

        user_name (str): username of valid user.

    Returns:
        User object with hash.
    """
    userobj=users.search("name:\""+user_name+"\"", rows=1)
    for user in userobj:
        user.pop('_version_', None)
        return user
    return None

#Documentation generation
def generate_documentation(docstring,document,request):
    request_rule=request.url_rule
    """
    Internal function for building documentation from docstring
    Parameters: 

        docstring (str): docstring with api lines.

    Returns:
        HTML or Markdown
    """
    current_route=""
    docjson=json.loads('{"methods":{}}')
    for rule in app.url_map.iter_rules():
        if request_rule==rule:
            print(rule)
            docjson['current_route']=str(request.url_rule).split("<")[0]
            print(rule.methods)
            for r in rule.methods:
                print(json.loads('{"'+r+'":[]}'))
                docjson['methods'][r]=[]

    #parse docstring
    # print(docjson)
    fields=[]
    for line in docstring.splitlines():
        if line.lstrip()[0:2]==";;":
            if line.lstrip().split(":",1)[0]==";;field":
                j=json.loads(line.split(":",1)[1])
                #Due to documentation route will always have a 'GET' method.
                docjson['methods']['GET'].append(j)
            if line.lstrip().split(":",1)[0]==";;gettablefieldnames":
                j=json.loads(line.split(":",1)[1])
                docjson['gettablefieldnames']=j                


    print(docjson)
    if document=="documentation.md":
        resp=make_response(render_template(document, docjson=docjson))
        resp.headers['Content-type'] = 'text/markdown; charset=UTF-8'
        return resp
    return render_template(document, docjson=docjson)

######################
#Routes and Handelers#
######################

#Resource interaction
@app.route("/api/resources/", defaults={'document': None}, methods = ['GET'])
@app.route("/api/resources/<document>", methods = ['GET'])
def learning_resources(document):

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
    
    

    ;;field:{"name":"title","type":"string","example":"DataONE","description":"The title of the learning resource."}
    ;;field:{"name":"url","type":"string","example":"dataoneorg.github.io","description":""}
    ;;field:{"name":"access_cost","type":"float","example":"1.0","description":""}
    ;;field:{"name":"submitter_name","type":"string","example":"\\\"Amber E Budden\\\"","description":""}
    ;;field:{"name":"submitter_email","type":"string","example":"example@example.com","description":""}
    ;;field:{"name":"author","type":"string","example":"Nhoebelheinrich","description":""}
    ;;field:{"name":"author_org","type":"string","example":"DataONE","description":""}
    ;;field:{"name":"contact","type":"string","example":"\\\"Nancy J.  Hoebelheinrich\\\"","description":""}
    ;;field:{"name":"contact_org","type":"string","example":"NASA","description":""}
    ;;field:{"name":"abstract.data","type":"string","example":"researchers","description":""}
    ;;field:{"name":"subject","type":"string","example":"Aerospace","description":""}
    ;;field:{"name":"keywords","type":"string","example":"\\\"Data management\\\"","description":""}
    ;;field:{"name":"licence","type":"string","example":"\\\"Creative Commons\\\"","description":""}
    ;;field:{"name":"usage_rights","type":"string","example":"USGS","description":""}
    ;;field:{"name":"citation.data","type":"string","example":"research","description":""}
    ;;field:{"name":"locator.data","type":"string","example":"\\\"10.5281/zenodo.239090\\\"","description":""}
    ;;field:{"name":"locator.type","type":"string","example":"DOI","description":""}
    ;;field:{"name":"publisher","type":"string","example":"\\\"Oak Ridge National Laboratory\\\"","description":""}
    ;;field:{"name":"version","type":"string","example":"\\\"1.0\\\"","description":""}
    ;;field:{"name":"access_features","type":"string","example":"Transformation","description":""}
    ;;field:{"name":"language_primary","type":"string","example":"es","description":""}
    ;;field:{"name":"languages_secondary","type":"string","example":"fr","description":""}
    ;;field:{"name":"ed_framework","type":"string","example":"\\\"FAIR Data Principles\\\"","description":""}
    ;;field:{"name":"ed_framework_dataone","type":"string","example":"Collect","description":""}
    ;;field:{"name":"ed_framework_fair","type":"string","example":"Findable","description":""}
    ;;field:{"name":"target_audience","type":"string","example":"\\\"Research scientist\\\"","description":""}
    ;;field:{"name":"purpose","type":"string","example":"\\\"Professional Development\\\"","description":""}
    ;;field:{"name":"completion_time","type":"string","example":"\\\"1 hour\\\"","description":""}
    ;;field:{"name":"media_type","type":"string","example":"\\\"Moving Image\\\"","description":""}
    ;;field:{"name":"type","type":"string","example":"\\\"Learning Activity\\\"","description":""}
    ;;field:{"name":"limit","type":"int","example":"15","description":"Maximum number of results to return. Default is 10"}
    ;;gettablefieldnames:["Name","Type","Example","Description"]
    """
    if document is None:
        document='search.json'
    allowed_documents=['search.json','documentation.html','documentation.md']
    
    if document not in  allowed_documents:
        return render_template('bad_document.html'), 400

    if request.method == 'GET':
        if document!="search.json":
            return generate_documentation(learning_resources.__doc__,document,request)
        returnval= json.loads('{ "documentation":"'+request.host_url+'api/resources/documentation.html","results":[]}')
        searchstring="status:true"
        
        searchstring=append_searchstring(searchstring,request,"title")
        searchstring=append_searchstring(searchstring,request,"url")
        searchstring=append_searchstring(searchstring,request,"access_cost")
        searchstring=append_searchstring(searchstring,request,"submitter_name")
        searchstring=append_searchstring(searchstring,request,"submitter_email")
        searchstring=append_searchstring(searchstring,request,"author")
        searchstring=append_searchstring(searchstring,request,"author_org")
        searchstring=append_searchstring(searchstring,request,"contact")
        searchstring=append_searchstring(searchstring,request,"contact_org")
        searchstring=append_searchstring(searchstring,request,"abstract.data")
        searchstring=append_searchstring(searchstring,request,"subject")
        searchstring=append_searchstring(searchstring,request,"keywords")
        searchstring=append_searchstring(searchstring,request,"licence")
        searchstring=append_searchstring(searchstring,request,"usage_rights")
        searchstring=append_searchstring(searchstring,request,"citation.data")
        searchstring=append_searchstring(searchstring,request,"locator.data")
        searchstring=append_searchstring(searchstring,request,"locator.type")
        searchstring=append_searchstring(searchstring,request,"publisher")
        searchstring=append_searchstring(searchstring,request,"version")
        searchstring=append_searchstring(searchstring,request,"created")
        searchstring=append_searchstring(searchstring,request,"published")
        searchstring=append_searchstring(searchstring,request,"access_features")
        searchstring=append_searchstring(searchstring,request,"language_primary")
        searchstring=append_searchstring(searchstring,request,"languages_secondary")
        searchstring=append_searchstring(searchstring,request,"ed_framework")
        searchstring=append_searchstring(searchstring,request,"ed_framework_dataone")
        searchstring=append_searchstring(searchstring,request,"ed_framework_fair")
        searchstring=append_searchstring(searchstring,request,"target_audience")
        searchstring=append_searchstring(searchstring,request,"purpose")
        searchstring=append_searchstring(searchstring,request,"completion_time")
        searchstring=append_searchstring(searchstring,request,"media_type")
        searchstring=append_searchstring(searchstring,request,"type")
        searchstring=append_searchstring(searchstring,request,"author")
        searchstring=append_searchstring(searchstring,request,"id")

        rows=10
        if request.args.get("limit"):
            if request.args.get("limit").isnumeric():
                rows=int(request.args.get("limit"))
        results=resources.search(searchstring, rows=rows)
        
        for result in results:
            result.pop('_version_', None)
            result.pop('status', None)
            if "contributors.firstname" in result.keys():
                result['contributors']=[]
                if result["contributors.firstname"]:
                    for i in range(len(result["contributors.firstname"])):
                        contributor=json.loads('{}')
                        contributor['firstname']=result["contributors.firstname"][i]
                        if "contributors.lastname" in result.keys():
                            contributor['lastname']=result["contributors.lastname"][i]
                        if "contributors.type" in result.keys():
                            contributor['type']=result["contributors.type"][i]
                        result['contributors'].append(contributor)
            if "contributor_orgs.name" in result.keys():
                result['contributor_orgs']=[]
                for i in range(len(result["contributor_orgs.name"])):
                    contributor=json.loads('{}')
                    contributor['name']=result["contributor_orgs.name"][i]
                    
                    if "contributor_orgs.type" in result.keys():
                        contributor['type']=result["contributor_orgs.type"][i]
                        
                    result['contributor_orgs'].append(contributor)
            result.pop('contributor_orgs.type', None)
            result.pop('contributor_orgs.name', None)
            result.pop('contributors.firstname', None)
            result.pop('contributors.lastname', None)
            result.pop('contributors.type', None)
            returnval['results'].append(result)

        returnval['hits-total']=results.hits
        returnval['hits-returned']=len(results)
        return returnval
    if request.method == 'POST':
        return "Method not yet implemented"
    if request.method == 'PUT':
        return "Method not yet implemented"
    if request.method == 'DELETE':
        return "Method not yet implemented"    
    #default return for HEAD
    return "HEAD"    

@app.route("/api/vocabularies/", methods = ['GET'])
def vocabularies():
    if request.method == 'GET':
        searchstring="*:*"
        returnval= json.loads('{ "documentation":"API documentation string will go here","names":[]}')
        if len(request.args)>0:
            if request.args.get("names")=="true":
                
                results=taxonomies.search("*:*")
                for result in results:
                    returnval["names"].append(result["name"])
                return returnval
            else:
                searchstring=append_searchstring(searchstring,request,"name")
                searchstring=append_searchstring(searchstring,request,"values")
                searchstring=append_searchstring(searchstring,request,"id")
                returnval= json.loads('{ "documentation":"API documentation string will go here","results":[]}')
                results=taxonomies.search(searchstring)
                for result in results:
                    result.pop('_version_', None)
                    returnval["results"].append(result)
                returnval['hits']=results.hits
                returnval['hits-returned']=len(results)
                return returnval
        else:
            returnval= json.loads('{ "documentation":"API documentation string will go here","results":[]}')
            results=taxonomies.search("*:*")
            for result in results:
                result.pop('_version_', None)
                returnval["results"].append(result)
            returnval['hits']=results.hits
            returnval['hits-returned']=len(results)
            return returnval

    

@app.route("/login/", methods = ['POST'])
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
    user_object=get_user(request.form['username'])
    if user_object:
        computed=user_object['hash']
        passwd=request.form['password']
        if drash.verify(passwd, computed):
            login_user(User(user_object['id'],user_object['groups'],user_object['name']))
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
    print(current_user.groups)
    return 'Logged in as: ' + current_user.name



@app.route("/")
def hello():
    return "DMT Clearinghouse."

@app.route("/static/<path:path>")
def send_static(path):
    print(path)
    return send_from_file('static',path)


if __name__ == "__main__":
    app.run()

