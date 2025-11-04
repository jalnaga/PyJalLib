import sys
from pathlib import Path

from pyjallib.perforce import Perforce
from orvlib.p4Sync import P4Sync

from P4 import P4, P4Exception

def connect_p4(port: str, user: str, client: str) -> P4:
    p4 = P4()
    p4.port = port
    p4.user = user
    p4.client = client
    p4.exception_level = 2
    try:
        p4.connect()
    except P4Exception as error:
        print(f"connect_p4 error: {error}")
    
    return p4

def disconnect_p4(p4: P4):
    try:
        p4.disconnect()
    except P4Exception as error:
        print(f"disconnect_p4 error: {error}")

def sync_folder(p4: P4, folder_path: str):
    try:
        p4.run("sync", folder_path + "/...#head")
    except P4Exception as error:
        print(f"sync_folder error: {error}")

def create_change_list(p4: P4, description: str) -> int:
    try:
        specs = p4.run("change", "-o")
        if not specs:
            print(f"create_change_list error: Empty result from p4 change -o")
            return 0
        
        spec = specs.pop(0)
        
        # spec이 딕셔너리인지 확인
        if not isinstance(spec, dict):
            print(f"create_change_list error: spec is not a dict, got {type(spec).__name__}: {spec}")
            return 0
        
        spec["Description"] = description
        print(f"create_change_list spec: {spec}")

        p4.input = spec
        result_list = p4.run("change", "-i")
        if not result_list:
            print(f"create_change_list error: Empty result from p4 change -i")
            return 0
        result = result_list.pop(0)
        if not isinstance(result, str):
            print(f"create_change_list error: result is not a string, got {type(result).__name__}: {result}")
            return 0
        change_number = int(result.split()[1])
        print("--------------------------------")
        return change_number
    except P4Exception as error:
        print(f"create_change_list error: {error}")
        return 0

def add_files_to_change_list(p4: P4, change_number: int, file_paths: list):
    for fp in file_paths:
        try:
            print(f"file path: {fp}")
            specs = p4.run("edit", "-c", str(change_number), fp)
            spec = specs.pop(0)
            if not isinstance(spec, dict):
                print(f"add_files_to_change_list error: spec is not a dict, got {type(spec).__name__}: {spec}")
                continue
            print(f"add_files_to_change_list spec: {spec}")
        except P4Exception as error:
            print(f"add_files_to_change_list error: {error}")
        print("--------------------------------")

def revert_unchanged_files(p4: P4, change_number: int):
    print("\n")
    try:
        specs = p4.run("revert", "-a", "-c", str(change_number))
        spec = specs.pop(0)
        
        if not isinstance(spec, dict):
            print(f"revert_unchanged_files error: spec is not a dict, got {type(spec).__name__}: {spec}")
            return
        print(f"revert_unchanged_files spec: {spec}")
    except P4Exception as error:
        print(f"revert_unchanged_files error: {error}")
    print("--------------------------------")

def revert_files(p4: P4, file_paths: list):
    print("\n")
    for fp in file_paths:
        try:
            print(f"file path: {fp}")
            specs = p4.run("revert", "-a", fp)
            spec = specs.pop(0)
            if not isinstance(spec, dict):
                print(f"revert_files error: spec is not a dict, got {type(spec).__name__}: {spec}")
                continue
            print(f"revert_files spec: {spec}")
        except P4Exception as error:
            print(f"revert_files error: {error}")
    print("--------------------------------")

def submit_change_list(p4: P4, change_number: int):
    print("\n")
    try:
        specs = p4.run("submit", "-c", str(change_number))
        spec = specs.pop(0)
        if not isinstance(spec, dict):
            print(f"submit_change_list error: spec is not a dict, got {type(spec).__name__}: {spec}")
            return
        print(f"submit_change_list spec: {spec}")
    except P4Exception as error:
        print(f"submit_change_list error: {error}")
    print("--------------------------------")

if __name__ == "__main__":
    # 환경 설정
    port = "PC-Build:1666"
    user = "Dev"
    client = "DongseokKim_DevStorage"

    p4 = connect_p4(port, user, client)
    print(f"Connected: {p4.connected()}")

    try:
        folder = r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit"
        sync_folder(p4, folder)

        target_files = [
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\A_Nm_Priest_M_BattleFist_Action_Hit_Back.max",
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\A_Nm_Priest_M_BattleFist_Action_Hit_Back.bip",
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\A_Nm_Priest_M_BattleFist_Action_Hit_Back.fbx",
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\A_Nm_Priest_M_BattleFist_Action_Hit_Back.json",
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\A_Nm_Priest_M_BattleFist_Action_Hit.max",
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\A_Nm_Priest_M_BattleFist_Action_Hit.bip",
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\A_Nm_Priest_M_BattleFist_Action_Hit.fbx",
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\A_Nm_Priest_M_BattleFist_Action_Hit.json",
            r"E:\DevStorage_root\DevStorage\Characters\NormalMonster\Priest\Male\Animation\BattleFist\Action\Hit\TestSWWWW.txt"
        ]

        cl = create_change_list(p4, "테스트임")
        add_files_to_change_list(p4, cl, target_files)
        # revert_files(p4, target_files)
        # revert_unchanged_files(p4, cl)
        # submit_change_list(p4, cl)

    finally:
        disconnect_p4(p4)
