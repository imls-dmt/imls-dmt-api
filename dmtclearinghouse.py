from flask import Flask, request, redirect, url_for
import pysolr
import json
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import drupal_hash_utility



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


######################
#Routes and Handelers#
######################

#Resrouce interaction
@app.route("/api/resources/", methods = ['GET'])
def learning_resources():

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
    """
    if request.method == 'GET':
        returnval= json.loads('{ "documentation":"API documentation string will go here","results":[]}')
        searchstring="status:true"
        
        searchstring=append_searchstring(searchstring,request,"title")
        searchstring=append_searchstring(searchstring,request,"status")
        searchstring=append_searchstring(searchstring,request,"url")
        searchstring=append_searchstring(searchstring,request,"access_cost")
        searchstring=append_searchstring(searchstring,request,"submitter_name")
        searchstring=append_searchstring(searchstring,request,"submitter_email")
        searchstring=append_searchstring(searchstring,request,"author")
        searchstring=append_searchstring(searchstring,request,"author_org")
        searchstring=append_searchstring(searchstring,request,"contact")
        searchstring=append_searchstring(searchstring,request,"contact_org")
        searchstring=append_searchstring(searchstring,request,"abstract")
        searchstring=append_searchstring(searchstring,request,"subject")
        searchstring=append_searchstring(searchstring,request,"keywords")
        searchstring=append_searchstring(searchstring,request,"licence")
        searchstring=append_searchstring(searchstring,request,"usage_rights")
        searchstring=append_searchstring(searchstring,request,"citation")
        searchstring=append_searchstring(searchstring,request,"locator")
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

