instance = context.getInstance()

if instance.state != "inactive":
    context.REQUEST.RESPONSE.redirect(context.absolute_url()+"?portal_status_message="+context.translate("Already started.", domain="alphaflow"))

instance.start("started through plone ui")
context.REQUEST.RESPONSE.redirect(context.absolute_url()+"?portal_status_message="+context.translate("Workflow started.", domain="alphaflow"))

