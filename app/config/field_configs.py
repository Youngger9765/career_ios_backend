"""
Tenant-specific field configurations for Client and Case forms
"""
from app.schemas.field_config import FieldSchema, FieldSection, FieldType, FormSchema


# ============================================================================
# CAREER TENANT - Client Form Configuration
# ============================================================================

CAREER_CLIENT_SECTIONS = [
    FieldSection(
        title="基本資料",
        description="個案基本資訊",
        order=1,
        fields=[
            FieldSchema(
                key="name",
                label="姓名",
                type=FieldType.TEXT,
                required=True,
                placeholder="請輸入真實姓名",
                help_text="使用者的真實姓名",
                order=1,
            ),
            FieldSchema(
                key="email",
                label="電子郵件地址",
                type=FieldType.EMAIL,
                required=True,
                placeholder="example@email.com",
                help_text="用於諮詢室或紀錄的連結",
                order=2,
            ),
            FieldSchema(
                key="phone",
                label="手機號碼",
                type=FieldType.PHONE,
                required=True,
                placeholder="0912345678",
                help_text="聯絡方式",
                order=3,
            ),
            FieldSchema(
                key="gender",
                label="性別",
                type=FieldType.SINGLE_SELECT,
                required=True,
                options=["男", "女", "其他", "不透露"],
                help_text="若業務有特別客群可彈性設定",
                order=4,
            ),
            FieldSchema(
                key="birth_date",
                label="生日（西元年）",
                type=FieldType.DATE,
                required=True,
                help_text="需可選年份（1900–2025）",
                validation_rules={"min_year": 1900, "max_year": 2025},
                order=5,
            ),
            FieldSchema(
                key="identity_option",
                label="身分選項",
                type=FieldType.SINGLE_SELECT,
                required=True,
                options=["學生", "社會新鮮人", "轉職者", "在職者", "其他"],
                help_text="例：學生／社會新鮮人／轉職者／在職者／其他",
                order=6,
            ),
            FieldSchema(
                key="current_status",
                label="目前現況",
                type=FieldType.TEXT,
                required=True,
                placeholder="例：探索中、準備轉職等",
                help_text="用於快速分類個案狀態",
                order=7,
            ),
            FieldSchema(
                key="education",
                label="學歷",
                type=FieldType.SINGLE_SELECT,
                required=False,
                options=["高中", "大學", "研究所", "博士", "其他"],
                help_text="可自定義補充",
                order=8,
            ),
            FieldSchema(
                key="current_job",
                label="您的現職（職業／年資）",
                type=FieldType.TEXT,
                required=False,
                placeholder="例：軟體工程師 / 3年",
                help_text="若求職者為學生或待業亦可填無",
                order=9,
            ),
            FieldSchema(
                key="career_status",
                label="職涯現況",
                type=FieldType.SINGLE_SELECT,
                required=False,
                options=["探索中", "轉職準備", "面試中", "已在職", "待業中"],
                help_text="例：探索中／轉職準備／面試中／已在職等",
                order=10,
            ),
            FieldSchema(
                key="has_consultation_history",
                label="過往諮詢經驗",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="是／否，若有請簡述",
                help_text="例：是否曾接受其他機構諮詢",
                order=11,
            ),
            FieldSchema(
                key="has_mental_health_history",
                label="心理或精神醫療史",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="是／否，若有請簡述（敏感資訊）",
                help_text="若為敏感資訊需加註提醒",
                order=12,
            ),
            FieldSchema(
                key="location",
                label="居住地區",
                type=FieldType.TEXT,
                required=False,
                placeholder="例：台北市",
                order=13,
            ),
            FieldSchema(
                key="notes",
                label="備註",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="其他需要記錄的資訊",
                help_text="諮商師私人備註",
                order=14,
            ),
        ],
    ),
]


# ============================================================================
# CAREER TENANT - Case Form Configuration
# ============================================================================

CAREER_CASE_SECTIONS = [
    FieldSection(
        title="個案資訊",
        description="個案編號、狀態與諮詢內容",
        order=1,
        fields=[
            FieldSchema(
                key="case_number",
                label="個案編號",
                type=FieldType.TEXT,
                required=True,
                placeholder="自動生成",
                help_text="系統自動生成，格式：CASE0001",
                order=1,
            ),
            FieldSchema(
                key="status",
                label="個案狀態",
                type=FieldType.SINGLE_SELECT,
                required=True,
                options=["0", "1", "2"],
                default_value="0",
                help_text="0=未進行(NOT_STARTED), 1=進行中(IN_PROGRESS), 2=已完成(COMPLETED)",
                order=2,
            ),
            FieldSchema(
                key="problem_description",
                label="問題敘述",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="請描述本次諮詢的問題與目的",
                help_text="用於理解本次諮詢重點",
                order=3,
            ),
            FieldSchema(
                key="goals",
                label="預期收穫",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="請描述本次諮詢的預期收穫",
                help_text="例：協助個案探索職涯方向、準備面試等",
                order=4,
            ),
            FieldSchema(
                key="summary",
                label="個案摘要",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="整體個案摘要",
                help_text="個案的整體情況描述",
                order=5,
            ),
        ],
    ),
]


# ============================================================================
# ISLAND TENANT - Client Form Configuration
# ============================================================================

ISLAND_CLIENT_SECTIONS = [
    FieldSection(
        title="基本資料",
        description="個案基本資訊",
        order=1,
        fields=[
            FieldSchema(
                key="name",
                label="姓名（或代號）",
                type=FieldType.TEXT,
                required=True,
                placeholder="可使用代號保護隱私",
                order=1,
            ),
            FieldSchema(
                key="email",
                label="聯絡信箱",
                type=FieldType.EMAIL,
                required=True,
                placeholder="example@email.com",
                order=2,
            ),
            FieldSchema(
                key="phone",
                label="聯絡電話",
                type=FieldType.PHONE,
                required=True,
                placeholder="0912345678",
                order=3,
            ),
            FieldSchema(
                key="gender",
                label="性別",
                type=FieldType.SINGLE_SELECT,
                required=True,
                options=["男", "女", "其他", "不願透露"],
                order=4,
            ),
            FieldSchema(
                key="birth_date",
                label="出生年月日",
                type=FieldType.DATE,
                required=True,
                validation_rules={"min_year": 1900, "max_year": 2025},
                order=5,
            ),
            FieldSchema(
                key="education",
                label="教育程度",
                type=FieldType.SINGLE_SELECT,
                required=False,
                options=["國中", "高中職", "大學", "研究所", "其他"],
                order=6,
            ),
            FieldSchema(
                key="location",
                label="居住地",
                type=FieldType.TEXT,
                required=False,
                order=7,
            ),
            FieldSchema(
                key="identity_option",
                label="身分狀態",
                type=FieldType.SINGLE_SELECT,
                required=True,
                options=["學生", "上班族", "待業中", "退休", "其他"],
                order=8,
            ),
            FieldSchema(
                key="current_status",
                label="目前狀況",
                type=FieldType.TEXT,
                required=True,
                placeholder="簡述目前身心狀況",
                order=9,
            ),
            FieldSchema(
                key="notes",
                label="其他備註",
                type=FieldType.TEXTAREA,
                required=False,
                order=10,
            ),
        ],
    ),
]


# ============================================================================
# ISLAND TENANT - Case Form Configuration
# ============================================================================

ISLAND_CASE_SECTIONS = [
    FieldSection(
        title="個案資訊",
        description="個案編號、狀態與諮商內容",
        order=1,
        fields=[
            FieldSchema(
                key="case_number",
                label="個案編號",
                type=FieldType.TEXT,
                required=True,
                placeholder="自動生成",
                order=1,
            ),
            FieldSchema(
                key="status",
                label="個案狀態",
                type=FieldType.SINGLE_SELECT,
                required=True,
                options=["0", "1", "2"],
                default_value="0",
                help_text="0=未進行(NOT_STARTED), 1=進行中(IN_PROGRESS), 2=已完成(COMPLETED)",
                order=2,
            ),
            FieldSchema(
                key="problem_description",
                label="問題敘述",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="請描述學生的問題與諮詢目的",
                help_text="用於理解本次諮詢重點",
                order=3,
            ),
            FieldSchema(
                key="goals",
                label="預期收穫",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="本次諮商的預期收穫",
                order=4,
            ),
            FieldSchema(
                key="summary",
                label="個案摘要",
                type=FieldType.TEXTAREA,
                required=False,
                placeholder="個案整體情況摘要",
                order=5,
            ),
        ],
    ),
]


# ============================================================================
# Configuration Registry
# ============================================================================

FIELD_CONFIGS = {
    "career": {
        "client": FormSchema(
            form_type="client",
            tenant_id="career",
            sections=CAREER_CLIENT_SECTIONS,
        ),
        "case": FormSchema(
            form_type="case",
            tenant_id="career",
            sections=CAREER_CASE_SECTIONS,
        ),
    },
    "island": {
        "client": FormSchema(
            form_type="client",
            tenant_id="island",
            sections=ISLAND_CLIENT_SECTIONS,
        ),
        "case": FormSchema(
            form_type="case",
            tenant_id="island",
            sections=ISLAND_CASE_SECTIONS,
        ),
    },
}


def get_field_config(tenant_id: str, form_type: str) -> FormSchema:
    """
    Get field configuration for a specific tenant and form type

    Args:
        tenant_id: Tenant identifier (e.g., 'career', 'island')
        form_type: Form type ('client' or 'case')

    Returns:
        FormSchema configuration

    Raises:
        ValueError: If tenant_id or form_type is invalid
    """
    if tenant_id not in FIELD_CONFIGS:
        raise ValueError(f"Unknown tenant_id: {tenant_id}")

    if form_type not in FIELD_CONFIGS[tenant_id]:
        raise ValueError(f"Unknown form_type: {form_type} for tenant {tenant_id}")

    return FIELD_CONFIGS[tenant_id][form_type]
