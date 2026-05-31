import json
from typing import Dict, Any, Optional, Iterator


class GraphQLHelper:
    def __init__(self, client, endpoint: str):
        self.client = client
        self.endpoint = endpoint

    def query(self, operation: str, fields: Dict[str, Any], variables: Optional[Dict] = None) -> Dict:
        q = self._build_query(operation, fields, variables)
        payload = {"query": q}
        if variables:
            payload["variables"] = variables
        resp = self.client.post(self.endpoint, json=payload)
        return resp.json()

    def _build_query(self, op: str, fields: Dict, variables: Optional[Dict]) -> str:
        fs = self._fields_to_str(fields)
        if variables:
            decl = ", ".join(f"${k}: String" for k in variables.keys())
            pass_vars = ", ".join(f"{k}: ${k}" for k in variables.keys())
            return f"query ({decl}) {{ {op}({pass_vars}) {{ {fs} }} }}"
        return f"query {{ {op} {{ {fs} }} }}"

    def _fields_to_str(self, fields: Dict) -> str:
        parts = []
        for k, v in fields.items():
            if v is True:
                parts.append(k)
            elif isinstance(v, dict):
                parts.append(f"{k} {{ {self._fields_to_str(v)} }}")
            elif isinstance(v, list) and v:
                parts.append(f"{k} {{ {self._fields_to_str(v[0])} }}")
        return " ".join(parts)

    def paginate(self, connection: str, page_size: int = 100) -> Iterator[Dict]:
        cursor = None
        while True:
            q = f"query {{ {connection}(first: {page_size}, after: {json.dumps(cursor)}) {{ edges {{ node }} pageInfo {{ hasNextPage endCursor }} }} }}"
            resp = self.client.post(self.endpoint, json={"query": q}).json()
            data = resp.get("data", {})
            conn = list(data.values())[0] if data else {}
            for edge in conn.get("edges", []):
                yield edge.get("node", {})
            if not conn.get("pageInfo", {}).get("hasNextPage"):
                break
            cursor = conn["pageInfo"]["endCursor"]
