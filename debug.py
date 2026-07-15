import store, export

a = [x for x in store.list_applications() if x["generated"]][0]
try:
    export.build_pdf(a["generated"])
    print("no crash?!")
except Exception as e:
    print("build_pdf crashed:", e)