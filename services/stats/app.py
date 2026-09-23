import os

from flasgger import Swagger
from flask import Flask, jsonify
from pymongo import MongoClient


def create_app(mongo_client=None):
    app = Flask(__name__)

    app.config["SWAGGER"] = {
        "title": "Task Manager Stats API",
        "uiversion": 3,
        "specs_route": "/apidocs/",
    }
    Swagger(
        app,
        template={
            "info": {
                "title": "Task Manager Stats API",
                "description": "Агрегована статистика по задачах (Лаб. робота №1, DevOps).",
                "version": "1.0.0",
            }
        },
    )

    if mongo_client is None:
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
        mongo_client = MongoClient(mongo_uri)

    db_name = os.environ.get("MONGO_DB", "taskmanager")
    db = mongo_client[db_name]
    tasks_collection = db["tasks"]

    @app.get("/health")
    def health():
        """Перевірка стану сервісу
        ---
        tags:
          - Health
        responses:
          200:
            description: Сервіс живий
        """
        return jsonify({"status": "ok"}), 200

    @app.get("/stats")
    def stats():
        """Отримати статистику по задачах
        ---
        tags:
          - Stats
        responses:
          200:
            description: Загальна кількість задач + розбивка за статусами
            examples:
              application/json: {"total": 5, "by_status": {"pending": 3, "done": 2}}
        """
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        by_status = {doc["_id"]: doc["count"] for doc in tasks_collection.aggregate(pipeline)}
        total = sum(by_status.values())
        return jsonify({"total": total, "by_status": by_status}), 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)