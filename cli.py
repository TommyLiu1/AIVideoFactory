import secrets
import click
from passlib.context import CryptContext

from service.db.user_db_service import UserDBService

click.command(name='create_db_user', help='创建数据库用户')
@click.option('--username', prompt='用户名', help='The username for the new database user.')
@click.option('--password', prompt='密码', hide_input=True, confirmation_prompt=True, help='The password for the new database user.')
@click.option('--user_type', type=click.Choice(['1', '2', '3'], case_sensitive=False), default='1', help='用户类型，1-runway共享，2-runway独享，3-即梦')
@click.option('--valid_from', prompt='有效期开始时间 (YYYY-MM-DD HH:MM:SS)', help='The start time of the user\'s validity period.')
@click.option('--valid_to', prompt='有效期结束时间 (YYYY-MM-DD HH:MM:SS)', help='The end time of the user\'s validity period.')
def create_db_user(username, password, user_type, valid_from, valid_to):
    """创建数据库用户"""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    salt = secrets.token_hex(16)  # 生成随机盐
    hashed_password = pwd_context.hash(password + salt)
    user = UserDBService.create_user(username=username, password=hashed_password,
                                     salt=salt,valid_from=valid_from, valid_to=valid_to, user_type=int(user_type))
    if not user:
        click.echo("用户创建失败，请检查输入信息是否正确。")
    click.echo("用户创建成功！")