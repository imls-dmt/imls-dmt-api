
    {% if 'GET' in docjson.methods %}
# GET method for {{docjson.current_route}}
## JS Example
``` js
$.ajax({
    url: "{{docjson.current_route}}{% if docjson.methods.GET.parameters|length > 0 %}?{{docjson.methods.GET.parameters[0].name}}={{docjson.methods.GET.parameters[0].example}}{% endif %}",
    

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
{% if docjson.methods.GET.parameters|length > 0 %}
## Available Fields
| {% for name in docjson.gettablefieldnames %}{{name}}{% if not loop.last %} | {% endif %}{% endfor %} |
| {% for name in docjson.gettablefieldnames %} --- {% if not loop.last %} | {% endif %}{% endfor %} |{% endif %}{% for field in docjson.methods.GET.parameters %}
| {{field.name}} | {{field.type}} | {{field.example}} | {{field.description}} |{% endfor %}
{% endif %}

{% if docjson.methods.GET.arguments|length > 0 %}
## Available Arguments
| Name | Description |
|  ---  | --- |{% for field in docjson.methods.GET.arguments %}
| {{field.name}} | {{field.description}} |{% endfor %}
{% endif %}
