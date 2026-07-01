#!/usr/bin/env python3
"""Create and auto-fill a DSW project filtered by a question tag.

This script targets a local DSW instance and produces:
1) A newly created project using the requested KM package.
2) A tagged question catalog with extracted answer options.
3) A filled questionnaire export JSON for downstream templating.
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://localhost:3000/wizard-api"
DEFAULT_PACKAGE_ORG = "research.data.no"
DEFAULT_PACKAGE_KM = "norway-generic"
DEFAULT_PACKAGE_VERSION = "1.2.1"
DEFAULT_TAG_NAME = "RCN/Science Europe"
# Stable for the Norway Generic 1.2.1 model in this DSW instance.
DEFAULT_TAG_UUID = "fd4637a2-a117-460a-a7fa-c03760c42629"


@dataclass
class ApiClient:
    base_url: str
    api_key: str

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        data = None
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(url=url, method=method, headers=headers, data=data)
        try:
            with urlopen(req) as resp:
                payload = resp.read().decode("utf-8")
                if not payload:
                    return None
                return json.loads(payload)
        except HTTPError as err:
            details = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {url} failed with {err.code}: {details}") from err

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, body: dict[str, Any]) -> Any:
        return self._request("POST", path, body)


def pick_package_uuid(packages_payload: dict[str, Any], org: str, km_id: str, version: str) -> str:
    for pkg in packages_payload.get("_embedded", {}).get("knowledgeModelPackages", []):
        if (
            pkg.get("organizationId") == org
            and pkg.get("kmId") == km_id
            and pkg.get("version") == version
        ):
            return pkg["uuid"]
    raise RuntimeError(
        f"Could not find package {org}:{km_id}:{version} in /knowledge-model-packages"
    )


def infer_tag_uuid(questionnaire: dict[str, Any], target_name: str, fallback_uuid: str) -> str:
    tags = questionnaire["knowledgeModel"]["entities"].get("tags", {})
    for tag_uuid, tag in tags.items():
        if (tag.get("name") or "").strip().lower() == target_name.strip().lower():
            return tag_uuid
    return fallback_uuid


def extract_tagged_question_catalog(
    km: dict[str, Any],
    tag_uuid: str,
) -> list[dict[str, Any]]:
    questions = km["entities"]["questions"]
    answers = km["entities"]["answers"]
    catalog: list[dict[str, Any]] = []

    for q_uuid, q in questions.items():
        tag_uuids = q.get("tagUuids", [])
        if tag_uuid not in tag_uuids:
            continue
        option_items = []
        for a_uuid in q.get("answerUuids", []) or []:
            a = answers.get(a_uuid, {})
            option_items.append(
                {
                    "answerUuid": a_uuid,
                    "label": a.get("label"),
                    "followUpUuids": a.get("followUpUuids", []),
                }
            )
        catalog.append(
            {
                "questionUuid": q_uuid,
                "title": q.get("title"),
                "text": q.get("text"),
                "questionType": q.get("questionType"),
                "valueType": q.get("valueType"),
                "tagUuids": tag_uuids,
                "listQuestionUuid": q.get("listQuestionUuid"),
                "itemTemplateQuestionUuids": q.get("itemTemplateQuestionUuids", []),
                "answerOptions": option_items,
            }
        )

    catalog.sort(key=lambda x: (x.get("title") or "", x["questionUuid"]))
    return catalog


def smart_text(title: str, value_type: str) -> str:
    t = (title or "").strip()
    if value_type == "EmailQuestionValueType":
        return "data.steward@mlclimate.example.org"
    if value_type == "UrlQuestionValueType":
        return "https://example.org/ml-climate-research"
    if value_type == "DateQuestionValueType":
        return date.today().isoformat()
    if value_type == "NumberQuestionValueType":
        return "3"
    if "title" in t.lower() and "dmp" in t.lower():
        return "Machine Learning Climate Research Project DMP"
    if "grant" in t.lower():
        return "RCN-MLC-2026-001"
    if "institution" in t.lower() or "partner" in t.lower():
        return "Norwegian Climate Analytics Lab"
    if "license" in t.lower():
        return "CC BY 4.0"
    if value_type == "StringQuestionValueType":
        return "Machine-learning-ready climate data and model artifacts"
    return (
        "This project uses reproducible machine learning workflows for climate research, "
        "with FAIR-aligned metadata, governance, and controlled access where required."
    )


def answer_rank(label: str) -> int:
    l = (label or "").strip().lower()
    if l in {"yes", "ja"}:
        return 100
    if "yes" in l or "ja" in l:
        return 90
    if "open" in l or "public" in l:
        return 80
    if l in {"no", "nei"}:
        return 10
    return 50


def post_set_reply(client: ApiClient, project_uuid: str, path: str, value: dict[str, Any]) -> bool:
    event = {
        "type": "SetReplyEvent",
        "uuid": str(uuid.uuid4()),
        "path": path,
        "value": value,
    }
    try:
        client.post(f"/projects/{project_uuid}/events", event)
        return True
    except RuntimeError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Agentic DSW project creation + auto-answering")
    parser.add_argument("--api-key-file", default=".dsw-api-key")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--package-org", default=DEFAULT_PACKAGE_ORG)
    parser.add_argument("--package-km", default=DEFAULT_PACKAGE_KM)
    parser.add_argument("--package-version", default=DEFAULT_PACKAGE_VERSION)
    parser.add_argument("--tag-name", default=DEFAULT_TAG_NAME)
    parser.add_argument("--tag-uuid", default=DEFAULT_TAG_UUID)
    parser.add_argument("--out-dir", default="out")
    args = parser.parse_args()

    api_key = Path(args.api_key_file).read_text(encoding="utf-8").strip()
    if not api_key:
        raise RuntimeError(f"Empty API key in {args.api_key_file}")

    client = ApiClient(base_url=args.base_url, api_key=api_key)
    packages = client.get("/knowledge-model-packages?page=0&size=200")
    package_uuid = pick_package_uuid(
        packages,
        org=args.package_org,
        km_id=args.package_km,
        version=args.package_version,
    )

    project_name = "Machine Learning Climate Research Project DMP"
    create_body = {
        "name": project_name,
        "knowledgeModelPackageUuid": package_uuid,
        "visibility": "PrivateProjectVisibility",
        "sharing": "RestrictedProjectSharing",
        "questionTagUuids": [args.tag_uuid],
    }
    new_project = client.post("/projects", create_body)
    project_uuid = new_project["uuid"]

    questionnaire = client.get(f"/projects/{project_uuid}/questionnaire")
    km = questionnaire["knowledgeModel"]
    tag_uuid = infer_tag_uuid(questionnaire, args.tag_name, args.tag_uuid)

    # If fallback was wrong, keep visibility with the discovered tag where possible.
    if tag_uuid != args.tag_uuid:
        print(f"[info] discovered tag uuid for '{args.tag_name}': {tag_uuid}")

    question_catalog = extract_tagged_question_catalog(km, tag_uuid)

    questions = km["entities"]["questions"]
    answers = km["entities"]["answers"]
    chapters = km["entities"]["chapters"]
    chapter_uuids = km.get("chapterUuids", [])

    answered_paths: set[str] = set()
    list_item_by_path: dict[str, str] = {}
    list_items_by_question_uuid: dict[str, list[str]] = {}

    def contains_tagged_descendant(question_uuid: str, memo: dict[str, bool]) -> bool:
        if question_uuid in memo:
            return memo[question_uuid]
        if question_uuid not in questions:
            memo[question_uuid] = False
            return False
        q = questions[question_uuid]
        if tag_uuid in (q.get("tagUuids") or []):
            memo[question_uuid] = True
            return True
        for a_uuid in q.get("answerUuids", []) or []:
            for f_uuid in answers.get(a_uuid, {}).get("followUpUuids", []):
                if contains_tagged_descendant(f_uuid, memo):
                    memo[question_uuid] = True
                    return True
        for child in q.get("itemTemplateQuestionUuids", []) or []:
            if contains_tagged_descendant(child, memo):
                memo[question_uuid] = True
                return True
        memo[question_uuid] = False
        return False

    descendant_memo: dict[str, bool] = {}

    def should_process(question_uuid: str) -> bool:
        return contains_tagged_descendant(question_uuid, descendant_memo)

    def choose_single_answer_uuid(q: dict[str, Any]) -> str | None:
        candidate_uuids = q.get("answerUuids", []) or []
        if not candidate_uuids:
            return None
        scored = []
        for a_uuid in candidate_uuids:
            a = answers.get(a_uuid, {})
            label = a.get("label") or ""
            follow_ups = a.get("followUpUuids", [])
            coverage = sum(1 for f in follow_ups if contains_tagged_descendant(f, descendant_memo))
            score = answer_rank(label) + coverage * 20
            scored.append((score, a_uuid))
        scored.sort(reverse=True)
        return scored[0][1]

    def answer_question(path: str, question_uuid: str) -> None:
        if path in answered_paths:
            return
        if question_uuid not in questions:
            return
        if not should_process(question_uuid):
            return

        q = questions[question_uuid]
        q_type = q.get("questionType")
        q_title = q.get("title") or ""
        q_value_type = q.get("valueType") or ""

        if q_type == "ValueQuestion":
            value = {
                "type": "StringReply",
                "value": smart_text(q_title, q_value_type),
            }
            if post_set_reply(client, project_uuid, path, value):
                answered_paths.add(path)
            return

        if q_type == "IntegrationQuestion":
            value = {
                "type": "IntegrationReply",
                "value": {
                    "type": "PlainType",
                    "value": f"{q_title}: Climate-ML project specific entry",
                },
            }
            if post_set_reply(client, project_uuid, path, value):
                answered_paths.add(path)
            return

        if q_type == "OptionsQuestion":
            answer_uuid = choose_single_answer_uuid(q)
            if answer_uuid is None:
                return
            value = {"type": "AnswerReply", "value": answer_uuid}
            if post_set_reply(client, project_uuid, path, value):
                answered_paths.add(path)
                for child_uuid in answers.get(answer_uuid, {}).get("followUpUuids", []):
                    answer_question(f"{path}.{answer_uuid}.{child_uuid}", child_uuid)
            return

        if q_type == "MultiChoiceQuestion":
            candidate_uuids = q.get("answerUuids", []) or []
            # Pick up to 2 high-signal options to keep replies coherent while opening follow-ups.
            scored = []
            for a_uuid in candidate_uuids:
                label = answers.get(a_uuid, {}).get("label") or ""
                scored.append((answer_rank(label), a_uuid))
            scored.sort(reverse=True)
            chosen = [a_uuid for _, a_uuid in scored[:2]] if scored else []
            if not chosen and candidate_uuids:
                chosen = [candidate_uuids[0]]
            value = {"type": "MultiChoiceReply", "value": chosen}
            if post_set_reply(client, project_uuid, path, value):
                answered_paths.add(path)
                for a_uuid in chosen:
                    for child_uuid in answers.get(a_uuid, {}).get("followUpUuids", []):
                        answer_question(f"{path}.{a_uuid}.{child_uuid}", child_uuid)
            return

        if q_type == "ListQuestion":
            item_uuid = str(uuid.uuid4())
            value = {"type": "ItemListReply", "value": [item_uuid]}
            if post_set_reply(client, project_uuid, path, value):
                answered_paths.add(path)
                list_item_by_path[path] = item_uuid
                list_items_by_question_uuid.setdefault(question_uuid, []).append(item_uuid)
                for child_uuid in q.get("itemTemplateQuestionUuids", []) or []:
                    answer_question(f"{path}.{item_uuid}.{child_uuid}", child_uuid)
            return

        if q_type == "ItemSelectQuestion":
            list_question_uuid = q.get("listQuestionUuid")
            candidates = list_items_by_question_uuid.get(list_question_uuid or "", [])
            if not candidates:
                # Create fallback item in list question if we can find its root path.
                for chapter_uuid in chapter_uuids:
                    for root_q in chapters[chapter_uuid].get("questionUuids", []):
                        if root_q == list_question_uuid:
                            fallback_path = f"{chapter_uuid}.{root_q}"
                            answer_question(fallback_path, root_q)
                            candidates = list_items_by_question_uuid.get(list_question_uuid or "", [])
                            break
                    if candidates:
                        break
            if not candidates:
                return
            value = {"type": "ItemSelectReply", "value": candidates[0]}
            if post_set_reply(client, project_uuid, path, value):
                answered_paths.add(path)
            return

    for chapter_uuid in chapter_uuids:
        chapter = chapters[chapter_uuid]
        for q_uuid in chapter.get("questionUuids", []):
            answer_question(f"{chapter_uuid}.{q_uuid}", q_uuid)

    final_questionnaire = client.get(f"/projects/{project_uuid}/questionnaire")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = out_dir / "rcn_science_europe_question_catalog.json"
    export_path = out_dir / "machine_learning_climate_dmp_export.json"
    summary_path = out_dir / "machine_learning_climate_dmp_summary.json"

    catalog_path.write_text(json.dumps(question_catalog, indent=2), encoding="utf-8")
    export_path.write_text(json.dumps(final_questionnaire, indent=2), encoding="utf-8")

    summary = {
        "projectUuid": project_uuid,
        "projectName": project_name,
        "package": f"{args.package_org}:{args.package_km}:{args.package_version}",
        "packageUuid": package_uuid,
        "tagName": args.tag_name,
        "tagUuid": tag_uuid,
        "taggedQuestionCount": len(question_catalog),
        "replyCount": len(final_questionnaire.get("replies", {})),
        "outputFiles": {
            "questionCatalog": str(catalog_path),
            "questionnaireExport": str(export_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
