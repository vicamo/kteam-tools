def jira_meta_field(jira, issue, field):
    field_ = "{}: ".format(field)
    for comment in jira.comments(issue):
        if comment.body.startswith(field_):
            return comment.body.removeprefix(field_)
    return None
