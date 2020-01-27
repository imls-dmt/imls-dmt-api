
    {% if 'GET' in docjson.methods %}
# GET method for {{docjson.current_route}}
## JS Example
``` js
$.ajax({
    url: "{{docjson.current_route}}?{{docjson.methods.GET[0].name}}={{docjson.methods.GET[0].example}}",
    type: 'GET',
    success: function (data, status) {
        if (status == 'success') {
            //If the request was successful parse the data.
            //This example will print out the title of the first result to console
            console.log(data.results[0].title)
        }else{
            //If the request failed, handle this response.
            console.log(status)
        };
    }
});
```
## Available Fields
| {% for name in docjson.gettablefieldnames %}{{name}}{% if not loop.last %} | {% endif %}{% endfor %} |
| {% for name in docjson.gettablefieldnames %} --- {% if not loop.last %} | {% endif %}{% endfor %} |{% endif %}{% for field in docjson.methods.GET %}
| {{field.name}} | {{field.type}} | {{field.example}} | {{field.description}} |{% endfor %}
