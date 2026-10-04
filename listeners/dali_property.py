from notion.pages import get_page, update_page_properties


DALI_PROPERTY_DATA_SOURCE_ID = "3ea7613b-20a9-8026-97d1-000b7e8aef4f"


class DaliPropertyListener:

    def handle(self, page_id):
        print(
            f"[DaliPropertyListener] "
            f"开始处理 page_id: {page_id}"
        )

        # ========================================================
        # 1. 读取当前房源
        # ========================================================

        page = get_page(page_id)
        properties = page["properties"]

        # ========================================================
        # 2. 检查「房源ID」
        # ========================================================

        property_id_prop = properties.get(
            "房源ID",
            {}
        )

        property_id = self.extract_text(
            property_id_prop
        )

        print(
            f"[DaliPropertyListener] "
            f"当前房源ID: {property_id!r}"
        )

        # 已经存在，不重复处理
        if property_id:
            return {
                "status": "UNCHANGED",
                "page_id": page_id,
                "reason": "PROPERTY_ID_EXISTS",
                "property_id": property_id,
            }

        # ========================================================
        # 3. 读取「片区」
        # ========================================================

        area_prop = properties.get(
            "片区",
            {}
        )

        area = area_prop.get(
            "select",
            {}
        )

        area_name = area.get("name")

        print(
            f"[DaliPropertyListener] "
            f"片区: {area_name!r}"
        )

        if not area_name:
            return {
                "status": "SKIPPED",
                "page_id": page_id,
                "reason": "AREA_EMPTY",
            }

        # ========================================================
        # 4. 提取 # 后面的英文
        # ========================================================

        if "#" not in area_name:
            return {
                "status": "ERROR",
                "page_id": page_id,
                "reason": "AREA_FORMAT_INVALID",
                "area": area_name,
            }

        area_code = area_name.split(
            "#",
            1
        )[1].strip().upper()

        if not area_code:
            return {
                "status": "ERROR",
                "page_id": page_id,
                "reason": "AREA_CODE_EMPTY",
                "area": area_name,
            }

        print(
            f"[DaliPropertyListener] "
            f"片区代码: {area_code}"
        )

        # ========================================================
        # 5. 读取 Notion 自动 ID
        # ========================================================

        id_prop = properties.get(
            "ID",
            {}
        )

        auto_id = self.extract_auto_id(
            id_prop
        )

        if auto_id is None:
            return {
                "status": "ERROR",
                "page_id": page_id,
                "reason": "AUTO_ID_EMPTY",
            }

        print(
            f"[DaliPropertyListener] "
            f"自动ID: {auto_id}"
        )

        # ========================================================
        # 6. 生成房源ID
        #
        # DL + 片区代码 + 00 + 自动ID
        # ========================================================

        generated_id = (
            f"DL"
            f"{area_code}"
            f"00"
            f"{auto_id}"
        )

        print(
            f"[DaliPropertyListener] "
            f"生成房源ID: {generated_id}"
        )

        # ========================================================
        # 7. 写入「房源ID」
        # ========================================================

        update_page_properties(
            page_id,
            {
                "房源ID": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": generated_id
                            }
                        }
                    ]
                }
            }
        )

        print(
            f"[DaliPropertyListener] "
            f"已写入房源ID: {generated_id}"
        )

        # ========================================================
        # 8. 回读验证
        # ========================================================

        updated_page = get_page(
            page_id
        )

        updated_property_id = self.extract_text(
            updated_page["properties"].get(
                "房源ID",
                {}
            )
        )

        if updated_property_id != generated_id:
            raise RuntimeError(
                "房源ID回读验证失败："
                f"期望={generated_id!r}, "
                f"实际={updated_property_id!r}"
            )

        print(
            "[DaliPropertyListener] "
            "房源ID写入 + 回读验证成功"
        )

        return {
            "status": "UPDATED",
            "page_id": page_id,
            "property_id": generated_id,
            "area": area_name,
            "area_code": area_code,
            "auto_id": auto_id,
            "verified": True,
        }

    @staticmethod
    def extract_text(prop):
        return "".join(
            item.get(
                "plain_text",
                ""
            )
            for item in prop.get(
                "rich_text",
                []
            )
        )

    @staticmethod
    def extract_auto_id(prop):
        unique_id = prop.get(
            "unique_id"
        )

        if not unique_id:
            return None

        number = unique_id.get(
            "number"
        )

        if number is None:
            return None

        return number
