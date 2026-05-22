"""
数据库配置模块
支持MySQL和Redis
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis

# MySQL配置（来自1.md）
MYSQL_CONFIG = {
    'host': '14.103.124.109',
    'port': 3306,
    'database': 'jianli',
    'user': 'jianli',
    'password': 'aS4QKY5znfZDn4Ts'
}

# Redis配置（来自1.md）
REDIS_CONFIG = {
    'host': '14.103.124.109',
    'port': 6379,
    'password': 'redis_b3ZReQ',
    'db': 9,
    'decode_responses': True
}

# 创建MySQL连接URL
DATABASE_URL = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}?charset=utf8mb4"

# SQLAlchemy引擎
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis客户端
redis_client = redis.Redis(**REDIS_CONFIG)

# 数据库模型定义
class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_name = Column(String(100), index=True)
    industry = Column(String(50))
    file_path = Column(String(500))
    parsed_data = Column(JSON)
    tci_score = Column(Float)
    dimensional_scores = Column(JSON)
    dimension_weights = Column(JSON)
    penalty_applied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Ranking(Base):
    __tablename__ = "rankings"
    
    id = Column(Integer, primary_key=True, index=True)
    industry = Column(String(50), index=True)
    candidate_name = Column(String(100))
    rank = Column(Integer)
    tci_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

# 依赖注入函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_redis():
    return redis_client

# 初始化数据库
def init_database():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")

if __name__ == "__main__":
    init_database()
