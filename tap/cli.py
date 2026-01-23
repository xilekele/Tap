"""CLI入口模块"""

import sys
import argparse
from .config import get_config
from .commands import CheckCommand, FlushCommand


def add_config_subparser(subparsers):
    """添加config子命令"""
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_subparsers = config_parser.add_subparsers(dest='config_action', help='配置操作')
    
    # set子命令
    set_parser = config_subparsers.add_parser('set', help='设置配置项')
    set_parser.add_argument('key', help='配置项名称 (APP_ID, APP_SECRET, app_token)')
    set_parser.add_argument('value', help='配置值')
    
    # show子命令
    show_parser = config_subparsers.add_parser('show', help='显示配置')
    
    # check子命令
    check_parser = config_subparsers.add_parser('check', help='检查配置是否完整')


def handle_config(args):
    """处理config命令"""
    config = get_config()
    
    if args.config_action == 'set':
        key = args.key.upper()
        value = args.value
        
        if key == 'APP_ID':
            config.app_id = value
        elif key == 'APP_SECRET':
            config.app_secret = value
        elif key == 'APP_TOKEN':
            config.app_token = value
        else:
            print(f"❌ 不支持的配置项: {key}")
            print("支持的配置项: APP_ID, APP_SECRET, app_token")
            sys.exit(1)
        
        config.save()
        print(f"✅ 已设置 {key}")
    
    elif args.config_action == 'show':
        print("📋 当前配置:")
        print(f"   APP_ID: {'*' * (len(config.app_id) if config.app_id else 0) if config.app_id else '未设置'}")
        print(f"   APP_SECRET: {'*' * (len(config.app_secret) if config.app_secret else 0) if config.app_secret else '未设置'}")
        print(f"   app_token: {config.app_token or '未设置'}")
        if config.tenant_access_token:
            print("   tenant_access_token: 已获取")
    
    elif args.config_action == 'check':
        if config.is_configured():
            print("✅ 配置完整")
        else:
            print("❌ 配置不完整")
            if not config.app_id:
                print("   - 缺少 APP_ID")
            if not config.app_secret:
                print("   - 缺少 APP_SECRET")
    
    else:
        config_parser.print_help()


def add_check_subparser(subparsers):
    """添加check子命令"""
    check_parser = subparsers.add_parser('check', help='校验文件字段与数据表字段是否匹配')
    check_parser.add_argument('file_path', help='Excel/CSV文件路径')
    check_parser.add_argument('--frozen-zone', default='0:5', help='冻结区域列范围，数字索引，格式: start:end 或单个数字 (默认: 0:5，对应A-F列)')
    check_parser.add_argument('--data-zone', default='6:25', help='数据区域列范围，数字索引，格式: start:end 或单个数字 (默认: 6:25，对应G-Z列)')
    check_parser.add_argument('--table-id', required=True, help='数据表ID')


def handle_check(args):
    """处理check命令"""
    cmd = CheckCommand(
        file_path=args.file_path,
        frozen_zone=args.frozen_zone,
        data_zone=args.data_zone,
        table_id=args.table_id
    )
    success = cmd.run()
    sys.exit(0 if success else 1)


def add_flush_subparser(subparsers):
    """添加flush子命令"""
    flush_parser = subparsers.add_parser('flush', help='同步数据到飞书多维表格')
    flush_parser.add_argument('file_path', help='Excel/CSV文件路径')
    flush_parser.add_argument('--frozen-zone', default='0:5', help='冻结区域列范围，数字索引，格式: start:end 或单个数字 (默认: 0:5，对应A-F列)')
    flush_parser.add_argument('--data-zone', default='6:25', help='数据区域列范围，数字索引，格式: start:end 或单个数字 (默认: 6:25，对应G-Z列)')
    flush_parser.add_argument('--table-id', required=True, help='数据表ID')
    flush_parser.add_argument('--mode', default='record', choices=['field', 'record'], 
                              help='同步模式 (默认: record)')


def handle_flush(args):
    """处理flush命令"""
    cmd = FlushCommand(
        file_path=args.file_path,
        frozen_zone=args.frozen_zone,
        data_zone=args.data_zone,
        table_id=args.table_id,
        mode=args.mode
    )
    success, stats = cmd.run()
    sys.exit(0 if success else 1)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        prog='tap',
        description='Tap - 飞书多维表格CLI工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  tap config set APP_ID xxx
  tap config set APP_SECRET xxx
  tap config set app_token xxx
  
  tap check /path/to/file.xlsx --table-id tblxxx
  
  tap flush /path/to/file.xlsx --table-id tblxxx
  tap flush /path/to/file.xlsx --table-id tblxxx --mode field
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 添加子命令
    add_config_subparser(subparsers)
    add_check_subparser(subparsers)
    add_flush_subparser(subparsers)
    
    args = parser.parse_args()
    
    if args.command == 'config':
        handle_config(args)
    elif args.command == 'check':
        handle_check(args)
    elif args.command == 'flush':
        handle_flush(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
