"""语言管理器"""
from typing import Dict, Optional
from src.i18n import zh, en  # 添加英文导入

class I18nManager:
    _instance = None
    _current_lang = 'zh'  # 保持中文为默认语言
    _translations: Dict[str, Dict[str, str]] = {
        'zh': zh.TRANSLATIONS,
        'en': en.TRANSLATIONS  # 添加英文翻译
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_text(cls, key: str, lang: Optional[str] = None) -> str:
        """获取指定语言的文本"""
        use_lang = lang or cls._current_lang
        try:
            return cls._translations[use_lang][key]
        except KeyError:
            return key  # 如果找不到翻译，返回原key
            
    @classmethod
    def set_language(cls, lang: str):
        """设置当前语言"""
        if lang in cls._translations:
            cls._current_lang = lang
            
    @classmethod
    def add_language(cls, lang: str, translations: Dict[str, str]):
        """添加新的语言支持"""
        cls._translations[lang] = translations
    
    @classmethod
    def get_current_lang(cls) -> str:
        """获取当前语言"""
        return cls._current_lang

# 创建便捷函数
def t(key: str) -> str:
    """获取当前语言的文本"""
    return I18nManager.get_text(key) 