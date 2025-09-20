'''
@Project ：tiangong 
@File    ：run_trainer_tests.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 

训练器测试运行脚本
'''

import unittest
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def run_all_tests():
    """运行所有训练器测试"""
    print("=" * 60)
    print("开始运行训练器模块测试")
    print("=" * 60)
    
    # 发现并运行测试
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_trainer.py')
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果统计
    print("\n" + "=" * 60)
    print("测试结果统计:")
    print(f"运行测试数: {result.testsRun}")
    print(f"失败数: {len(result.failures)}")
    print(f"错误数: {len(result.errors)}")
    print(f"跳过数: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    print("=" * 60)
    
    return result.wasSuccessful()


def run_specific_test_class(test_class_name):
    """运行特定的测试类"""
    print(f"运行测试类: {test_class_name}")
    print("=" * 60)
    
    # 导入测试模块
    from test_trainer import *
    
    # 获取测试类
    test_class = globals().get(test_class_name)
    if not test_class:
        print(f"未找到测试类: {test_class_name}")
        return False
    
    # 运行测试类
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_specific_test_method(test_class_name, test_method_name):
    """运行特定的测试方法"""
    print(f"运行测试方法: {test_class_name}.{test_method_name}")
    print("=" * 60)
    
    # 导入测试模块
    from test_trainer import *
    
    # 获取测试类
    test_class = globals().get(test_class_name)
    if not test_class:
        print(f"未找到测试类: {test_class_name}")
        return False
    
    # 运行特定测试方法
    suite = unittest.TestSuite()
    test_method = test_class(test_method_name)
    suite.addTest(test_method)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """主函数"""
    if len(sys.argv) == 1:
        # 运行所有测试
        success = run_all_tests()
    elif len(sys.argv) == 2:
        # 运行特定测试类
        test_class_name = sys.argv[1]
        success = run_specific_test_class(test_class_name)
    elif len(sys.argv) == 3:
        # 运行特定测试方法
        test_class_name = sys.argv[1]
        test_method_name = sys.argv[2]
        success = run_specific_test_method(test_class_name, test_method_name)
    else:
        print("用法:")
        print("  python run_trainer_tests.py                    # 运行所有测试")
        print("  python run_trainer_tests.py TestClass          # 运行特定测试类")
        print("  python run_trainer_tests.py TestClass test_method  # 运行特定测试方法")
        return
    
    if success:
        print("\n✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 有测试失败！")
        sys.exit(1)


if __name__ == '__main__':
    main()
