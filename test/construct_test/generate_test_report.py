'''
@Project ：tiangong 
@File    ：generate_test_report.py
@IDE     ：PyCharm 
@Author  ：Skyrim
@Date    ：2025/9/17 21:24 

训练器测试报告生成器
'''

import unittest
import sys
import os
import time
import json
from datetime import datetime
from io import StringIO

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from test_config import TestConfig, TEST_CASES


class TestReportGenerator:
    """测试报告生成器"""
    
    def __init__(self, output_dir="./test_reports"):
        self.output_dir = output_dir
        self.report_data = {
            'timestamp': datetime.now().isoformat(),
            'test_suites': [],
            'summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'skipped': 0,
                'total_time': 0
            }
        }
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
    
    def run_all_tests(self):
        """运行所有测试并生成报告"""
        print("开始运行训练器测试套件...")
        print("=" * 60)
        
        start_time = time.time()
        
        # 运行基础功能测试
        self._run_test_suite('test_trainer', '基础功能测试')
        
        # 运行性能测试
        self._run_test_suite('test_trainer_performance', '性能测试')
        
        end_time = time.time()
        self.report_data['summary']['total_time'] = end_time - start_time
        
        # 生成报告
        self._generate_html_report()
        self._generate_json_report()
        self._print_summary()
    
    def _run_test_suite(self, test_module, suite_name):
        """运行测试套件"""
        print(f"\n运行 {suite_name}...")
        print("-" * 40)
        
        try:
            # 导入测试模块
            if test_module == 'test_trainer':
                from test_trainer import *
            elif test_module == 'test_trainer_performance':
                from test_trainer_performance import *
            else:
                raise ImportError(f"未找到测试模块: {test_module}")
            
            # 发现测试
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromName(test_module)
            
            # 运行测试
            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=2)
            result = runner.run(suite)
            
            # 记录结果
            suite_data = {
                'name': suite_name,
                'module': test_module,
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
                'output': stream.getvalue(),
                'details': {
                    'failures': [{'test': str(test), 'traceback': traceback} 
                               for test, traceback in result.failures],
                    'errors': [{'test': str(test), 'traceback': traceback} 
                             for test, traceback in result.errors]
                }
            }
            
            self.report_data['test_suites'].append(suite_data)
            
            # 更新总结
            self.report_data['summary']['total_tests'] += result.testsRun
            self.report_data['summary']['passed'] += result.testsRun - len(result.failures) - len(result.errors)
            self.report_data['summary']['failed'] += len(result.failures)
            self.report_data['summary']['errors'] += len(result.errors)
            self.report_data['summary']['skipped'] += suite_data['skipped']
            
            # 打印结果
            print(f"测试结果: {result.testsRun} 个测试")
            print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
            print(f"失败: {len(result.failures)}")
            print(f"错误: {len(result.errors)}")
            
            if result.failures:
                print("\n失败的测试:")
                for test, traceback in result.failures:
                    print(f"  - {test}")
            
            if result.errors:
                print("\n错误的测试:")
                for test, traceback in result.errors:
                    print(f"  - {test}")
            
        except Exception as e:
            print(f"运行测试套件失败: {e}")
            suite_data = {
                'name': suite_name,
                'module': test_module,
                'error': str(e),
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0
            }
            self.report_data['test_suites'].append(suite_data)
    
    def _generate_html_report(self):
        """生成HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>训练器测试报告</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ background-color: #e8f4f8; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .suite {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .error {{ color: orange; }}
        .details {{ background-color: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 3px; }}
        pre {{ background-color: #f0f0f0; padding: 10px; border-radius: 3px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>训练器测试报告</h1>
        <p>生成时间: {self.report_data['timestamp']}</p>
    </div>
    
    <div class="summary">
        <h2>测试总结</h2>
        <p>总测试数: {self.report_data['summary']['total_tests']}</p>
        <p class="success">通过: {self.report_data['summary']['passed']}</p>
        <p class="failure">失败: {self.report_data['summary']['failed']}</p>
        <p class="error">错误: {self.report_data['summary']['errors']}</p>
        <p>跳过: {self.report_data['summary']['skipped']}</p>
        <p>总用时: {self.report_data['summary']['total_time']:.2f}秒</p>
    </div>
"""
        
        # 添加测试套件详情
        for suite in self.report_data['test_suites']:
            status_class = 'success' if suite['failures'] == 0 and suite['errors'] == 0 else 'failure'
            
            html_content += f"""
    <div class="suite">
        <h3 class="{status_class}">{suite['name']}</h3>
        <p>模块: {suite['module']}</p>
        <p>测试数: {suite['tests_run']}</p>
        <p>失败: {suite['failures']}</p>
        <p>错误: {suite['errors']}</p>
        
        <div class="details">
            <h4>测试输出:</h4>
            <pre>{suite.get('output', '无输出')}</pre>
        </div>
"""
            
            # 添加失败和错误详情
            if suite['details']['failures']:
                html_content += """
        <div class="details">
            <h4>失败的测试:</h4>
"""
                for failure in suite['details']['failures']:
                    html_content += f"""
            <div>
                <strong>{failure['test']}</strong>
                <pre>{failure['traceback']}</pre>
            </div>
"""
            
            if suite['details']['errors']:
                html_content += """
        <div class="details">
            <h4>错误的测试:</h4>
"""
                for error in suite['details']['errors']:
                    html_content += f"""
            <div>
                <strong>{error['test']}</strong>
                <pre>{error['traceback']}</pre>
            </div>
"""
            
            html_content += "    </div>"
        
        html_content += """
</body>
</html>
"""
        
        # 保存HTML报告
        html_path = os.path.join(self.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\nHTML报告已生成: {html_path}")
    
    def _generate_json_report(self):
        """生成JSON报告"""
        json_path = os.path.join(self.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.report_data, f, indent=2, ensure_ascii=False)
        
        print(f"JSON报告已生成: {json_path}")
    
    def _print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print(f"总测试数: {self.report_data['summary']['total_tests']}")
        print(f"通过: {self.report_data['summary']['passed']}")
        print(f"失败: {self.report_data['summary']['failed']}")
        print(f"错误: {self.report_data['summary']['errors']}")
        print(f"跳过: {self.report_data['summary']['skipped']}")
        print(f"总用时: {self.report_data['summary']['total_time']:.2f}秒")
        
        success_rate = (self.report_data['summary']['passed'] / 
                       max(self.report_data['summary']['total_tests'], 1)) * 100
        print(f"成功率: {success_rate:.1f}%")
        
        if self.report_data['summary']['failed'] > 0 or self.report_data['summary']['errors'] > 0:
            print("\n❌ 有测试失败或错误！")
        else:
            print("\n✅ 所有测试通过！")


def main():
    """主函数"""
    generator = TestReportGenerator()
    generator.run_all_tests()


if __name__ == '__main__':
    main()
