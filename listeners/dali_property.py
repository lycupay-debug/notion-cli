from notion.pages import retrieve_page, update_page


DALI_PROPERTY_DATA_SOURCE_ID = (
    "3ea7613b-20a9-8026-97d1-000b7e8aef4f"
)


class DaliPropertyListener:

    def handle(self, page_id):
        print(
            f"[DaliPropertyListener] "
            f"开始处理 page_id: {page_id}"
        )

        # ========================================================
        # 1. 读取当前页面
        # ========================================================

        page = retrieve_page(page_id)

        properties = page.get(
            "properties",
            {}
        )

        # ========================================================
        # 2. 读取「房源ID公式」
        # ========================================================

        formula_prop = properties.get(
            "房源ID公式",
            {}
        )

        formula_value = self.extract_formula_text(
            formula_prop
        )

        print(
            f"[DaliPropertyListener] "
            f"房源ID公式结果: {formula_value!r}"
        )

        # ========================================================
        # 3. 公式结果为空
        #
        # 不执行任何写入。
        # ========================================================

        if not formula_value:
            print(
                "[DaliPropertyListener] "
                "房源ID公式结果为空，跳过写入"
            )

            return {
                "status": "SKIPPED",
                "page_id": page_id,
                "reason": "PROPERTY_ID_FORMULA_EMPTY",
            }

        # ========================================================
        # 4. 读取当前「房源ID」
        #
        # 这里只用于日志。
        # 不参与判断。
        # 无论原来有没有内容，都直接覆盖。
        # ========================================================

        current_property_id = self.extract_text(
            properties.get(
                "房源ID",
                {}
            )
        )

        print(
            f"[DaliPropertyListener] "
            f"当前房源ID: {current_property_id!r}"
        )

        print(
            f"[DaliPropertyListener] "
            f"准备更新为: {formula_value!r}"
        )

        # ========================================================
        # 5. 覆盖写入「房源ID」
        # ========================================================

        update_page(
            page_id,
            {
                "房源ID": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": formula_value
                            }
                        }
                    ]
                }
            }
        )

        print(
            f"[DaliPropertyListener] "
            f"已写入房源ID: {formula_value}"
        )

        # ========================================================
        # 6. 回读验证
        # ========================================================

        updated_page = get_page(
            page_id
        )

        updated_property_id = self.extract_text(
            updated_page.get(
                "properties",
                {}
            ).get(
                "房源ID",
                {}
            )
        )

        if updated_property_id != formula_value:
            raise RuntimeError(
                "房源ID回读验证失败："
                f"期望={formula_value!r}, "
                f"实际={updated_property_id!r}"
            )

        print(
            "[DaliPropertyListener] "
            "房源ID写入 + 回读验证成功"
        )

        # ========================================================
        # 7. 返回执行结果
        # ========================================================

        return {
            "status": "UPDATED",
            "page_id": page_id,
            "property_id": formula_value,
            "source": "房源ID公式",
            "previous_property_id": current_property_id,
            "verified": True,
        }

    @staticmethod
    def extract_text(prop):
        """
        提取 Notion rich_text 的纯文本。
        """
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
    def extract_formula_text(prop):
        """
        提取 Notion formula 属性计算后的字符串结果。

        预期结构：

        {
            "type": "formula",
            "formula": {
                "type": "string",
                "string": "DLCC001"
            }
        }

        不重新计算公式。
        只读取 Notion 已经计算完成的最终结果。
        """

        formula = prop.get(
            "formula"
        )

        if not isinstance(
            formula,
            dict
        ):
            return ""

        formula_type = formula.get(
            "type"
        )

        if formula_type != "string":
            return ""

        value = formula.get(
            "string"
        )

        if value is None:
            return ""

        return str(value).strip()