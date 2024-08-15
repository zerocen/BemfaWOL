#!/bin/env python3

import os
import re
import sys
import socket
import threading
import struct
import time
import subprocess
import logging
from logging.handlers import RotatingFileHandler

# 巴法云参数
server_ip = 'bemfa.com'
server_port = 8344
client_id = ""  # 私钥
topid = ""  # 主题
heartbeat_interval = 30

# 主机参数
pc_user = ""
pc_ip = ""
mac = ""


def init_logger():
    logger = logging.getLogger('my_logger')
    logger.setLevel(logging.DEBUG)
    # 创建一个handler，用于写入日志文件
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    fh = RotatingFileHandler(os.path.join(logs_dir, "wol.log"), maxBytes=1024*1024*5, backupCount=3)
    fh.setLevel(logging.DEBUG)
    # 创建一个handler，用于输出到控制台
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.DEBUG)
    # 定义handler的输出格式
    formatter = logging.Formatter('[%(asctime)s] - %(levelname)-7s - %(message)s')
    fh.setFormatter(formatter)
    # ch.setFormatter(formatter)
    # 给logger添加handler
    logger.addHandler(fh)
    # logger.addHandler(ch)
    return logger


logger = init_logger()


def connect_to_server(server_ip, server_port, client_id, topid):
    global tcp_client_socket
    while True:
        try:
            # 连接服务器
            tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_client_socket.connect((server_ip, server_port))
            # 发送订阅指令
            substr = f'cmd=1&uid={client_id}&topic={topid}\r\n'
            tcp_client_socket.send(substr.encode("utf-8"))
            res = tcp_client_socket.recv(1024).decode('utf-8')
            logger.debug(f'Recv data for subscription: {res.strip()}')

            if "cmd=1&res=1" in res:
                logger.debug(f'Subscribed topic: {topid}')
            else:
                raise Exception(f"failed to subscribe topic: {topid}")
            break
        except socket.error as e:
            tcp_client_socket.close()
            logger.error(f"Failed to connect to server: {e}.")
            time.sleep(2)


def send_heartbeat():
    # 发送心跳, 获取远程PC状态
    keeplive = f'cmd=9&uid={client_id}&topic={topid}\r\n'
    tcp_client_socket.send(keeplive.encode("utf-8"))


def start_heartbeat_timer():
    try:
        send_heartbeat()
    except socket.error as e:
        tcp_client_socket.close()
        logger.error(f"Error sending heartbeat: {e}\nTry to reconnect to server...")
        time.sleep(2)
        connect_to_server(server_ip, server_port, client_id, topid)

    threading.Timer(heartbeat_interval, start_heartbeat_timer).start()


def update_bemfa_msg(client_id, topid, msg):
    update_str = f"cmd=2&uid={client_id}&topic={topid}/up&msg={msg}"
    tcp_client_socket.send(update_str.encode("utf-8"))
    res = tcp_client_socket.recv(1024).decode('utf-8')
    logger.debug(f"Recv data for update message: {res.strip()}")

    if "cmd=2&res=1" in res:
        logger.debug(f'Last message is updated for topic {topid}')
    else:
        raise Exception(f"failed to update bemfa message for topic {topid}")


def wakeup_pc(mac="", ip=""):
    if len(mac) != 17:
        raise ValueError("MAC address should be set as form 'XX:XX:XX:XX:XX:XX'")
    mac_address = mac.replace(":", '')
    data = ''.join(['FFFFFFFFFFFF', mac_address * 20])
    send_data = b''
 
    for i in range(0, len(data), 2):
        send_data = b''.join([send_data, struct.pack('B', int(data[i: i + 2], 16))])
    # print(send_data)
 
    # 通过socket广播出去，为避免失败，间隔广播三次
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(send_data, (ip, 7))
        time.sleep(1)
        sock.sendto(send_data, (ip, 7))
        time.sleep(1)
        sock.sendto(send_data, (ip, 7))
    except Exception as e:
        raise Exception(f"Failed to send wakeup packet: {e}")


def turn_off_pc(user, address):
    try:
        # 需要提前将服务器公钥添加到PC上
        subprocess.run(["ssh", f"{user}@{address}", "shutdown /h"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    except subprocess.TimeoutExpired as e:
        logger.warning(f'SSH command timeout: {e}')


def get_pc_status(ip):
    if sys.platform == "win32":
        params = ['ping', '-n', "1", '-w', "2000", ip]
    else:
        params = ["ping", "-c", "1", "-W", "2", ip]

    result = subprocess.run(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return "on" if result.returncode == 0 else "off"


def main():
    connect_to_server(server_ip, server_port, client_id, topid)
    start_heartbeat_timer()
    
    logger.info("Bemfa cloud is connected")
    while True:
        # 接收服务器发送过来的数据
        try:
            recv_data = tcp_client_socket.recv(1024)
        except:
            time.sleep(10)
            continue

        if len(recv_data) != 0:
            res = recv_data.decode('utf-8')
            logger.debug(f'Recv data from bemfa: {res.strip()}')
            
            try:
                cmd_match = re.search(r"cmd=(\d)", res)
                msg_match = re.search(r"msg=(\S+)", res)
                cmd = cmd_match.group(1)
                msg = msg_match.group(1) if msg_match else None

                if cmd == "2":
                    if not msg:
                        raise Exception(f"No message for command {cmd}")

                    logger.debug(f'Received message from topic {topid}: {msg}')
                    if msg == "on":
                        try:
                            logger.info("Turning on my pc...")
                            wakeup_pc(mac, pc_ip)
                        except Exception as e:
                            raise Exception(f"Failed to turn on my pc: {e}")
                    elif msg == "off":
                        try:
                            logger.info("Shutting down my pc...")
                            turn_off_pc(pc_user, pc_ip)
                        except Exception as e:
                            raise Exception(f"Failed to shutting down my pc: {e}")
                    else:
                        logger.info(f"Unsupported action: {msg}")

                elif cmd == "9":
                    if not msg:
                        raise Exception(f"No message for command {cmd}")
                    
                    logger.debug(f'Got last message of the topic {topid}: {msg}')
                    real_status = get_pc_status(pc_ip)
                    if real_status != msg:
                        logger.info(f"The PC status on bemfa is '{msg}' while the real PC status is '{real_status}'")
                        update_bemfa_msg(client_id, topid, real_status)
                        logger.info(f"PC status on bemfa is updated to '{real_status}'")
                
            except Exception as e:
                logger.error(f"{e}")
                time.sleep(2)

        else:
            logger.error("Connection Error")
            time.sleep(2)
            tcp_client_socket.close()
            connect_to_server(server_ip, server_port, client_id, topid)


main()