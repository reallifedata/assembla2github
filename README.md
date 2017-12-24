# assembla2github
## migrate assembla tickets -> github issues

### features/function
migrates a full assembla site's tickets/milestones to github's issue format
* Ticket status -> issue status (open/closed)
* Ticket comment/conversation history
* Ticket user assignment
* Original assembla ticket number preserved
* Ticket/milestone associations
 
**repeatable** - can execute multiple times. The generated issues/milestone names are prefixed with the original assembla ID numbers. Pre-existing issues/milestones having names which start with assembla identifiers will be updated with new information and not duplicated

### installation/setup
1. install python runtime (2 or 3)
2. install PyGithub library
3. in assembla source site go to settings -> export and import -> submit a request to export your tickets. the request is queued and may take several minutes. Youll eventually gain access to a downloadable backup of assembla tickets in a JSON-like format.
4. edit the top of the assembla2github.py file, there are several project-specific mappings you must customize such as user and status mappings
5. run the python script such as:
```
python assembla2github.py --username=mygithubloginname --password=mygithubpassword --dumpfile=/path/to/jsonfile.js --repository=mygithubrepository --verbose=True
```
