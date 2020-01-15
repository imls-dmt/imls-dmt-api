from flask import Flask, request
import pysolr
import json

#Create flask app
app = Flask(__name__)
#Pull config info from file
app.config.from_object('dmtconfig.DevConfig')
#Create a pysolr object for accessing the "learningresources" index
resources = pysolr.Solr(app.config["SOLR_ADDRESS"]+"learningresources/", timeout=10)


##################
#Shared Functions#
##################
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
        if request.args.get(name).isalpha():
            return searchstring+" AND "+name+":"+request.args.get(name)
        else:
            return searchstring
    else:
        return searchstring



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
        
        #Number of rows returned
        rows=10
        if request.args.get("rows"):
            if request.args.get("rows").isnumeric():
                rows=int(request.args.get("rows"))
 
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

        returnval['hits']=results.hits
        returnval['hits-returned']=len(results)
        return returnval
    if request.method == 'POST':
        return "Method not yet implemented"
    if request.method == 'PUT':
        return "Method not yet implemented"
    if request.method == 'DELETE':
        return "Method not yet implemented"    

@app.route("/")
def hello():
    return "DMT Clearinghouse."

@app.route("/static/<path:path>")
def send_static(path):
    print(path)
    return send_from_file('static',path)


if __name__ == "__main__":
    app.run()

