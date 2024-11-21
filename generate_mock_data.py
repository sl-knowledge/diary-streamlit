import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from mock_data import generate_mock_data, verify_mock_data
    
    print("开始生成模拟数据...")
    if generate_mock_data():
        print("模拟数据生成成功！")
        verify_mock_data()
    else:
        print("模拟数据生成失败！请检查日志获取详细信息。") 