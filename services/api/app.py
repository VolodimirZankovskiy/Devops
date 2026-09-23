import os
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from flasgger import Swagger
from flask import Flask, jsonify, request
from pymongo import MongoClient


def create_app(mongo_client=None):
    """Application factory.

    Accepting an already-created mongo_client makes the app easy to test:
    unit tests can pass in a mongomock.MongoClient(), integration tests can
    pass in a real pymongo.MongoClient() pointed at a test database.
    """
    app = Flask(__name__)

    app.config["SWAGGER"] = {
        "title": "Task Manager API",
        "uiversion": 3,
        "specs_route": "/apidocs/",
    }
    Swagger(
        app,
        template={
            "info": {
                "title": "Task Manager API",
                "description": "CRUD API для управління задачами (Лаб. робота №1, DevOps).",
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

    def serialize(task):
        return {
            "id": str(task["_id"]),
            "title": task["title"],
            "description": task.get("description", ""),
            "status": task.get("status", "pending"),
            "created_at": task.get("created_at"),
        }

    def parse_object_id(task_id):
        try:
            return ObjectId(task_id)
        except (InvalidId, TypeError):
            return None

    @app.get("/health")
    def health():
        """Перевірка стану сервісу
        ---
        tags:
          - Health
        responses:
          200:
            description: Сервіс живий
            examples:
              application/json: {"status": "ok"}
        """
        return jsonify({"status": "ok"}), 200

    @app.post("/tasks")
    def create_task():
        """Створити нову задачу
        ---
        tags:
          - Tasks
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - title
              properties:
                title:
                  type: string
                  example: Зробити лабу 1
                description:
                  type: string
                  example: Dockerfile + docker-compose
                status:
                  type: string
                  example: pending
        responses:
          201:
            description: Задачу створено
          400:
            description: title є обов'язковим полем
        """
        data = request.get_json(silent=True) or {}
        title = data.get("title")
        if not title:
            return jsonify({"error": "title is required"}), 400

        task = {
            "title": title,
            "description": data.get("description", ""),
            "status": data.get("status", "pending"),
            "created_at": datetime.utcnow().isoformat(),
        }
        result = tasks_collection.insert_one(task)
        task["_id"] = result.inserted_id
        return jsonify(serialize(task)), 201

    @app.get("/tasks")
    def list_tasks():
        """Отримати список задач
        ---
        tags:
          - Tasks
        parameters:
          - in: query
            name: status
            type: string
            required: false
            description: Фільтр за статусом (наприклад, pending або done)
        responses:
          200:
            description: Список задач
        """
        status = request.args.get("status")
        query = {"status": status} if status else {}
        tasks = [serialize(t) for t in tasks_collection.find(query)]
        return jsonify(tasks), 200

    @app.get("/tasks/<task_id>")
    def get_task(task_id):
        """Отримати одну задачу за id
        ---
        tags:
          - Tasks
        parameters:
          - in: path
            name: task_id
            type: string
            required: true
        responses:
          200:
            description: Задача знайдена
          400:
            description: Невалідний id
          404:
            description: Задачу не знайдено
        """
        oid = parse_object_id(task_id)
        if oid is None:
            return jsonify({"error": "invalid id"}), 400
        task = tasks_collection.find_one({"_id": oid})
        if not task:
            return jsonify({"error": "not found"}), 404
        return jsonify(serialize(task)), 200

    @app.put("/tasks/<task_id>")
    def update_task(task_id):
        """Оновити задачу
        ---
        tags:
          - Tasks
        parameters:
          - in: path
            name: task_id
            type: string
            required: true
          - in: body
            name: body
            required: true
            schema:
              type: object
              properties:
                title:
                  type: string
                description:
                  type: string
                status:
                  type: string
                  example: done
        responses:
          200:
            description: Задачу оновлено
          400:
            description: Немає валідних полів для оновлення / невалідний id
          404:
            description: Задачу не знайдено
        """
        oid = parse_object_id(task_id)
        if oid is None:
            return jsonify({"error": "invalid id"}), 400

        data = request.get_json(silent=True) or {}
        update_fields = {
            key: value for key, value in data.items() if key in ("title", "description", "status")
        }
        if not update_fields:
            return jsonify({"error": "no valid fields to update"}), 400

        result = tasks_collection.update_one({"_id": oid}, {"$set": update_fields})
        if result.matched_count == 0:
            return jsonify({"error": "not found"}), 404

        task = tasks_collection.find_one({"_id": oid})
        return jsonify(serialize(task)), 200

    @app.delete("/tasks/<task_id>")
    def delete_task(task_id):
        """Видалити задачу
        ---
        tags:
          - Tasks
        parameters:
          - in: path
            name: task_id
            type: string
            required: true
        responses:
          204:
            description: Задачу видалено
          400:
            description: Невалідний id
          404:
            description: Задачу не знайдено
        """
        oid = parse_object_id(task_id)
        if oid is None:
            return jsonify({"error": "invalid id"}), 400

        result = tasks_collection.delete_one({"_id": oid})
        if result.deleted_count == 0:
            return jsonify({"error": "not found"}), 404
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
