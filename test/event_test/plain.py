'''
@Project ：SkyEngine 
@File    ：plain.py
@IDE     ：PyCharm
@Author  ：Skyrimforest
@Date    ：2025/10/8 10:35
'''
import numpy as np

result = {}
result.setdefault("skyrim", 233)
res = result.get("skyrim", 0)
print(res)
samples_poisson = np.random.poisson(lam=5, size=10)
print(samples_poisson)
samples_exponential = np.random.exponential(scale=2, size=1)
print(samples_exponential)
