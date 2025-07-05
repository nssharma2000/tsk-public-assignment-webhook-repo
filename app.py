from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__, static_folder = "static")
CORS(app)

#Connecting to MongoDB database
client = MongoClient("mongodb+srv://nssharma2000:nama1234@cluster0.oelsdrp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["ts_database"]
collection = db["events"]

seen_timestamps = set()

@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/webhook", methods=["POST"])     #Route for app to be notified of events
def webhook():
    data = request.json
    event_type = request.headers.get('X-GitHub-Event')

    event = {}
    now = datetime.now()    #Current date and time

    if event_type == "push":
        event = {                                            
            "type": "push",
            "author": data['pusher']['name'],
            "from_branch": None,
            "to_branch": data['ref'].split('/')[-1],
            "timestamp": now
        }  #Data for push event

    elif event_type == "pull_request":
        action = data['action']
        pr = data['pull_request']

        if action == "opened":
            event = {
                "type": "pull_request",
                "author": pr['user']['login'],
                "from_branch": pr['head']['ref'],
                "to_branch": pr['base']['ref'],
                "timestamp": now
            } #Data for pull request

        elif action == "closed" and pr.get("merged", False):
            event = {
                "type": "merge",
                "author": pr['user']['login'],
                "from_branch": pr['head']['ref'],
                "to_branch": pr['base']['ref'],
                "timestamp": now
            }  #Data for merge event

        else:
            return jsonify({"msg": "PR event ignored"}), 200

    else:
        return jsonify({"msg": "Event type ignored"}), 200

    collection.insert_one(event)         #Saving event to collection
    return jsonify({"Message": "Event stored"}), 200


@app.route("/get_events", methods=["GET"])   #Route for getting events
def get_events():
    results = []
    events = collection.find().sort("timestamp", -1).limit(10)  #Fetching events from collection, sorted in descending order (only the first 10 events)
    for e in events:
        timestamp_str = e["timestamp"].strftime('%-d %B %Y - %-I:%M %p UTC')
        key = f"{e['type']}:{e.get('author')}:{timestamp_str}"
        if key not in seen_timestamps:
            seen_timestamps.add(key)
            results.append({
                "type": e["type"],
                "author": e.get("author"),
                "from_branch": e.get("from_branch"),
                "to_branch": e.get("to_branch"),
                "timestamp": timestamp_str
            })
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, port=5000)