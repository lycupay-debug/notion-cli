from notion.pages import retrieve_page, update_page
from notion.databases import query_data_source


COURSE_RECORD_DATA_SOURCE_ID = "3e97613b-20a9-805f-9965-000b3f9c86fb"
BILL_DATA_SOURCE_ID = "3e97613b-20a9-8044-b3be-000be2f97973"


class CourseRecordListener:

    def handle(self, page_id):
        print(
            f"[CourseRecordListener] "
            f"开始处理 page_id: {page_id}"
        )

        # ========================================================
        # 1. 读取当前课程记录
        # ========================================================

        course_page = retrieve_page(page_id)
        course_properties = course_page["properties"]

        # ========================================================
        # 2. 读取「名称」
        # ========================================================

        name = self.extract_title(
            course_properties.get("名称", {})
        )

        print(
            f"[CourseRecordListener] "
            f"名称: {name!r}"
        )

        if not name:
            print(
                "[CourseRecordListener] "
                "名称为空，不处理"
            )

            return {
                "status": "SKIPPED",
                "reason": "NAME_EMPTY",
                "page_id": page_id,
            }

        # ========================================================
        # 3. 读取「日期」
        # ========================================================

        date_prop = course_properties.get("日期", {})
        date_value = date_prop.get("date")

        print(
            f"[CourseRecordListener] "
            f"日期: {date_value}"
        )

        if not date_value:
            print(
                "[CourseRecordListener] "
                "日期为空，不处理"
            )

            return {
                "status": "SKIPPED",
                "reason": "DATE_EMPTY",
                "page_id": page_id,
                "name": name,
            }

        # ========================================================
        # 4. 查询「💰账单」
        # ========================================================

        bills = self.query_all_data_source(
            BILL_DATA_SOURCE_ID
        )

        matched_bills = []

        for bill in bills:

            bill_properties = bill.get(
                "properties",
                {}
            )

            bill_name = self.extract_title(
                bill_properties.get("名称", {})
            )

            if bill_name == name:
                matched_bills.append(bill)

        print(
            f"[CourseRecordListener] "
            f"同名账单数量: {len(matched_bills)}"
        )

        # ========================================================
        # 5. 必须且只能存在一个同名账单
        # ========================================================

        if len(matched_bills) == 0:

            print(
                "[CourseRecordListener] "
                "未找到同名账单，不写入"
            )

            return {
                "status": "NO_MATCH",
                "page_id": page_id,
                "name": name,
            }

        if len(matched_bills) > 1:

            print(
                "[CourseRecordListener] "
                "发现多个同名账单，停止写入"
            )

            return {
                "status": "ERROR",
                "reason": "MULTIPLE_BILLS",
                "page_id": page_id,
                "name": name,
                "count": len(matched_bills),
            }

        # ========================================================
        # 6. 获取唯一账单
        # ========================================================

        bill = matched_bills[0]
        bill_page_id = bill["id"]

        print(
            f"[CourseRecordListener] "
            f"唯一账单: {bill_page_id}"
        )

        # ========================================================
        # 7. 查询「🔖课程记录」中所有同名记录
        # ========================================================

        course_records = self.query_all_data_source(
            COURSE_RECORD_DATA_SOURCE_ID
        )

        matched_course_records = []

        for record in course_records:

            record_properties = record.get(
                "properties",
                {}
            )

            record_name = self.extract_title(
                record_properties.get("名称", {})
            )

            if record_name == name:
                matched_course_records.append(record)

        course_record_ids = [
            record["id"]
            for record in matched_course_records
            if record.get("id")
        ]

        print(
            f"[CourseRecordListener] "
            f"同名课程记录数量: {len(course_record_ids)}"
        )

        if not course_record_ids:

            return {
                "status": "NO_COURSE_RECORD_MATCH",
                "page_id": page_id,
                "name": name,
                "bill_page_id": bill_page_id,
            }

        # ========================================================
        # 8. 读取账单「引用」Relation
        # ========================================================

        bill_page = retrieve_page(bill_page_id)

        bill_properties = bill_page["properties"]

        relation_prop = bill_properties.get(
            "引用",
            {}
        )

        relations = relation_prop.get(
            "relation",
            []
        )

        # 保留账单当前已有的引用及其原有顺序
        merged_ids = [
            item["id"]
            for item in relations
            if item.get("id")
        ]

        existing_ids = set(merged_ids)

        print(
            f"[CourseRecordListener] "
            f"账单已有引用数量: {len(existing_ids)}"
        )

        # ========================================================
        # 9. 将全部同名课程记录补充到「引用」
        #
        # 已存在：
        #     保留，不重复添加
        #
        # 不存在：
        #     追加
        #
        # 账单原有其他引用：
        #     保留
        # ========================================================

        added_ids = []

        for course_record_id in course_record_ids:

            if course_record_id not in existing_ids:

                merged_ids.append(
                    course_record_id
                )

                existing_ids.add(
                    course_record_id
                )

                added_ids.append(
                    course_record_id
                )

        print(
            f"[CourseRecordListener] "
            f"需要新增引用数量: {len(added_ids)}"
        )

        # ========================================================
        # 10. 没有任何变化，不写入
        # ========================================================

        if not added_ids:

            print(
                "[CourseRecordListener] "
                "账单「引用」已经包含全部同名课程记录，无需写入"
            )

            return {
                "status": "UNCHANGED",
                "page_id": page_id,
                "name": name,
                "bill_page_id": bill_page_id,
                "course_record_count": len(
                    course_record_ids
                ),
                "existing_relation_count": len(
                    merged_ids
                ),
                "added_count": 0,
                "verified": True,
            }

        # ========================================================
        # 11. 写入「引用」
        # ========================================================

        new_relations = [
            {
                "id": course_record_id
            }
            for course_record_id in merged_ids
        ]

        update_page(
            bill_page_id,
            {
                "引用": {
                    "relation": new_relations
                }
            }
        )

        print(
            "[CourseRecordListener] "
            f"已新增 {len(added_ids)} 条课程记录到账单「引用」"
        )

        # ========================================================
        # 12. 回读验证
        # ========================================================

        updated_bill = retrieve_page(
            bill_page_id
        )

        updated_relation = (
            updated_bill["properties"]
            .get("引用", {})
            .get("relation", [])
        )

        updated_ids = {
            item.get("id")
            for item in updated_relation
            if item.get("id")
        }

        # ========================================================
        # 13. 验证全部同名课程记录是否存在
        # ========================================================

        missing_ids = (
            set(course_record_ids)
            - updated_ids
        )

        if missing_ids:

            raise RuntimeError(
                "「引用」Relation 回读验证失败："
                f"缺少课程记录 {missing_ids}"
            )

        # ========================================================
        # 14. 验证成功
        # ========================================================

        print(
            "[CourseRecordListener] "
            "全部同名课程记录写入 + 回读验证成功"
        )

        return {
            "status": "UPDATED",
            "page_id": page_id,
            "name": name,
            "bill_page_id": bill_page_id,
            "course_record_count": len(
                course_record_ids
            ),
            "existing_relation_count": len(
                updated_ids
            ),
            "added_count": len(
                added_ids
            ),
            "verified": True,
        }

    @staticmethod
    def query_all_data_source(data_source_id):
        results = []
        cursor = None

        while True:
            response = query_data_source(
                data_source_id,
                start_cursor=cursor,
                page_size=100,
            )
            results.extend(response.get("results", []))

            if not response.get("has_more"):
                return results

            cursor = response.get("next_cursor")
            if not cursor:
                raise RuntimeError(
                    f"Data Source 分页返回 has_more=true，但 next_cursor 为空: {data_source_id}"
                )

    @staticmethod
    def query_all_data_source(data_source_id):
        results = []
        cursor = None

        while True:
            response = query_data_source(
                data_source_id,
                start_cursor=cursor,
                page_size=100,
            )
            results.extend(response.get("results", []))

            if not response.get("has_more"):
                return results

            cursor = response.get("next_cursor")
            if not cursor:
                raise RuntimeError(
                    f"Data Source 分页返回 has_more=true，但 next_cursor 为空: {data_source_id}"
                )

    # ============================================================
    # Title → 普通文本
    # ============================================================

    @staticmethod
    def extract_title(prop):

        return "".join(
            item.get(
                "plain_text",
                ""
            )
            for item in prop.get(
                "title",
                []
            )
        )