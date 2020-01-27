### Schema for the '{{collection}}' collection:

| Name | Type | Required | Multi-Value |
|---|---|:---:|:---:|{% for field in schemajson.fields %}
| {{field.name}} | {{field.type}} | {{field.required}} | {{field.multivalue}} |{% endfor %}
