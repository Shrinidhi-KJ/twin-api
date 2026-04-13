import json
import random
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from faker import Faker


def create_app(spec_path: str) -> FastAPI:
    fake = Faker()

    with open(spec_path, "r") as f:
        spec = json.load(f)

    all_schemas = spec.get("components", {}).get("schemas", {})

    def resolve_ref(ref_string):
        schema_name = ref_string.split("/")[-1]
        return all_schemas[schema_name]

    def smart_string_for_field(field_name, schema_context=""):
        fname = field_name.lower()
        ctx = schema_context.lower()
        if "email" in fname:
            return fake.email()
        if "phone" in fname:
            return fake.phone_number()
        if "url" in fname or "photourl" in fname:
            return fake.image_url()
        if "address" in fname:
            return fake.address().replace("\n", ", ")
        if "city" in fname:
            return fake.city()
        if "country" in fname:
            return fake.country()
        if "firstname" in fname:
            return fake.first_name()
        if "lastname" in fname:
            return fake.last_name()
        if "username" in fname:
            return fake.user_name()
        if "password" in fname:
            return fake.password()
        if fname == "name":
            if "pet" in ctx:
                return fake.first_name()
            if "category" in ctx or "tag" in ctx:
                return fake.word().capitalize()
            return fake.name()
        if "description" in fname or "bio" in fname:
            return fake.sentence()
        if "title" in fname:
            return fake.sentence(nb_words=4)
        return fake.word()

    def generate_field(field_def, field_name="", schema_context=""):
        if "$ref" in field_def:
            ref_name = field_def["$ref"].split("/")[-1]
            return generate_object(resolve_ref(field_def["$ref"]), ref_name)
        field_type = field_def.get("type")
        if "enum" in field_def:
            return random.choice(field_def["enum"])
        if field_type == "string":
            return smart_string_for_field(field_name, schema_context)
        if field_type == "integer":
            return fake.random_int(min=1, max=10000)
        if field_type == "number":
            return round(random.uniform(1, 1000), 2)
        if field_type == "boolean":
            return fake.boolean()
        if field_type == "array":
            item_def = field_def.get("items", {})
            count = random.randint(1, 3)
            return [generate_field(item_def, field_name, schema_context) for _ in range(count)]
        return None

    def generate_object(schema, schema_name=""):
        result = {}
        for field_name, field_def in schema.get("properties", {}).items():
            result[field_name] = generate_field(field_def, field_name, schema_name)
        return result

    def get_resource_from_path(path):
        parts = [p for p in path.split("/") if p and not p.startswith("{")]
        return parts[0] if parts else "default"

    def get_response_schema(operation):
        responses = operation.get("responses", {})
        success_response = responses.get("200") or responses.get("201") or {}
        content = success_response.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            return all_schemas.get(ref_name), ref_name, False
        if schema.get("type") == "array":
            items = schema.get("items", {})
            if "$ref" in items:
                ref_name = items["$ref"].split("/")[-1]
                return all_schemas.get(ref_name), ref_name, True
        return None, None, False

    databases = {}

    def seed_database(resource, schema, schema_name, count=10):
        databases.setdefault(resource, {})
        for _ in range(count):
            obj = generate_object(schema, schema_name)
            obj_id = obj.get("id") or fake.random_int(min=1, max=100000)
            obj["id"] = obj_id
            databases[resource][obj_id] = obj

    def path_specificity(path):
        return path.count("{")

    auth_required = len(spec.get("components", {}).get("securitySchemes", {})) > 0

    app = FastAPI(title=f"Mock {spec['info']['title']}")

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if request.url.path in ["/", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        if not auth_required:
            return await call_next(request)
        auth_header = request.headers.get("authorization") or request.headers.get("api_key")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing authentication. Provide 'Authorization: Bearer <token>' or 'api_key' header."},
            )
        return await call_next(request)

    @app.get("/")
    def root():
        return {
            "message": f"Mock server for {spec['info']['title']}",
            "resources": {r: len(db) for r, db in databases.items()},
            "auth_required": auth_required,
        }

    sorted_paths = sorted(spec["paths"].items(), key=lambda x: path_specificity(x[0]))

    for path, methods in sorted_paths:
        resource = get_resource_from_path(path)
        for method, operation in methods.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue
            response_schema, schema_name, is_array = get_response_schema(operation)
            if response_schema and resource not in databases:
                seed_database(resource, response_schema, schema_name)

            def make_handler(method, path, resource, schema, schema_name, is_array):
                async def handler(request: Request):
                    db = databases.get(resource, {})
                    if method == "get":
                        if "{" in path:
                            param_value = list(request.path_params.values())[0]
                            try:
                                param_value = int(param_value)
                            except ValueError:
                                pass
                            if param_value in db:
                                return db[param_value]
                            if schema:
                                obj = generate_object(schema, schema_name)
                                obj["id"] = param_value
                                return obj
                            raise HTTPException(status_code=404, detail="Not found")
                        return list(db.values())
                    if method == "post":
                        body = await request.json()
                        new_id = max(db.keys()) + 1 if db else 1
                        body["id"] = new_id
                        db[new_id] = body
                        return body
                    if method in ["put", "patch"]:
                        body = await request.json()
                        if "{" in path:
                            param_value = list(request.path_params.values())[0]
                            try:
                                param_value = int(param_value)
                            except ValueError:
                                pass
                            db[param_value] = body
                        return body
                    if method == "delete":
                        if "{" in path:
                            param_value = list(request.path_params.values())[0]
                            try:
                                param_value = int(param_value)
                            except ValueError:
                                pass
                            if param_value in db:
                                del db[param_value]
                                return {"message": "Deleted"}
                            raise HTTPException(status_code=404, detail="Not found")
                    return {}
                return handler

            handler_fn = make_handler(method, path, resource, response_schema, schema_name, is_array)
            app.add_api_route(
                path,
                handler_fn,
                methods=[method.upper()],
                summary=operation.get("summary", ""),
            )

    # Detect spec version and print summary
    spec_version = spec.get("openapi") or spec.get("swagger") or "unknown"
    print(f"Loaded spec: {spec['info']['title']}")
    print(f"Spec version: {spec_version}")
    print(f"Registered {len(spec['paths'])} paths")
    print(f"Resources seeded: {list(databases.keys())}")
    print(f"Auth required: {auth_required}")

    if not databases:
        print("\n⚠️  WARNING: No resources were seeded.")
        if str(spec_version).startswith("2."):
            print("   This appears to be a Swagger 2.0 spec.")
            print("   Currently only OpenAPI 3.x is fully supported.")
        else:
            print("   Check that the spec defines schemas under components.schemas")
        print()

    return app