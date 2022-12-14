#!/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3
from SystemConfiguration import SCDynamicStoreCopyConsoleUser
import os
import plistlib
import subprocess
import sys
import json
import time
from Foundation import NSLog
import requests
import tempfile

############################################## Initial variables and  JSON ######################################
dialogApp = "/Library/Application Support/Dialog/Dialog.app/Contents/MacOS/Dialog"
dialogPath = "/Library/Application Support/Dialog/Dialog.app"
dialog_command_file="/var/tmp/dialog.log"
infolink = ""
dep_nag_icon = "https://github.com/unfo33/venturewell-image/blob/main/dep-nag.png?raw=true"
content_base = {
        "button1text": "Send Notification",
        "button2text": "Defer",
        "alignment": "center",
        "bannerimage": "https://github.com/unfo33/venturewell-image/blob/main/dmun.jpeg?raw=true",
        "message": "VentureWell is migrating Device Management tools which requires manual user approval - don't worry it will only take a second!\n\nPlease click **Send Notification** below to kick off the process.\n\nIf you have any questions or concerns please feel free to reach out in Slack or email support@venturewell.org",
        "messagefont": "size=16",
        "title": "none",
        "moveable": 1,
        "ontop": 1
}

################################################ Functions #####################################################
if os.path.exists(dialog_command_file):
    os.remove(dialog_command_file)

def swiftDialog_Install(url, name):
    # download Install to temp directory
    new = requests.get(url, stream=True)
    with tempfile.TemporaryDirectory() as tmpdirname:
        with open(f"{tmpdirname}/{name}", 'wb') as f:
            f.write(new.content)
            write_log("Downloaded new file to temp directory")
            # check signature
            command = ["/usr/sbin/spctl", "-a", "-vv", "-t", "install", dialogPath]
            result = subprocess.run(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # if valid install
            if (str(result).find("PWA5E9TQ59") != "-1"):
                write_log("Verified signature and will now install")
                try:
                    command = ["/usr/sbin/installer", "-pkg", f"{tmpdirname}/{name}", "-target", "/"]
                    install = subprocess.run(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    write_log(f"Install results: {install}")
                except Exception as e:
                    write_log(f"failed to install package with error: {e}")
                    exit
            else:
                write_log("Signature validation failed - will not install")
                exit

def swiftDialog_Check():
    response = requests.get("https://api.github.com/repos/bartreardon/swiftDialog/releases/latest")
    url = (response.json()["assets"][0]["browser_download_url"])
    name = (response.json()["assets"][0]["name"])
    latest_Version = response.json()["tag_name"][1:]
    write_log(f"Latest version of swiftdialog is: {name}")
    if os.path.exists(dialogPath):
        with open(f"{dialogPath}/Contents/Info.plist", 'rb') as fp:
            p1 = plistlib.load(fp)
            current_Version = p1["CFBundleShortVersionString"]
            write_log(f"Current version of swiftdialog is: {current_Version}")
            if current_Version != latest_Version:
                write_log("Not on latest version")
                return False, url, name
            else:
                write_log("On latest version")
                return True, url, name
    else:
        write_log("Swiftdialog not installed.")
        return False, url, name

def content_step1():
    message = "## Notification has been sent\n\nIt is located in the Notification Center in the top right corner of your screen.\n\nClick anyhwere on the notification and a new window will open, select **Allow** and sign-in to finish device management setup.\n\nOnce completed you will be able to close this window."
    content_base.update({"button1text": "Done"})
    content_base.update({"button2text": "Try Again"})
    content_base.update({"message": message})
    content_base.pop("bannerimage", None)
    content_base.update({"icon": dep_nag_icon})
    content_base.update({"centericon": 1})
    content_base.update({"iconsize": "500"})
    content_base.update({"ontop": 0})
    exit = run_dialog(content_base)
    return exit.returncode
    

def content_Complete():
    message = "## Device has been updated, thanks!\n\nIf you have any questions or concerns please feel free to reach out in Slack or email support@venturewell.org"
    content_base.update({"button1text": "Close"})
    content_base.pop("button2text", None)
    content_base.pop("icon", None)
    content_base.update({"bannerimage": "https://github.com/unfo33/venturewell-image/blob/main/dmun.jpeg?raw=true"})
    content_base.update({"message": message})
    run_dialog(content_base)

def write_log(text):
    """logger for depnotify"""
    NSLog("[mdm-switch] " + text)

def content_Defer():
    message = "## Device update has been deferred or failed.\n\nWe will remind you again soon!"
    content_base.update({"button1text": "Close"})
    content_base.pop("button2text", None)
    content_base.pop("icon", None)
    content_base.update({"message": message})
    content_base.update({"bannerimage": "https://github.com/unfo33/venturewell-image/blob/main/dmun.jpeg?raw=true"})
    write_log("user deferred")
    run_dialog(content_base)

# check if DEP enabled
def is_dep_enabled():
    """Check if DEP is enabled"""
    cloud_record_path = "/private/var/db/ConfigurationProfiles/Settings"
    good_record = os.path.join(cloud_record_path, ".cloudConfigRecordFound")
    bad_record = os.path.join(cloud_record_path, ".cloudConfigRecordNotFound")
    no_activation = os.path.join(cloud_record_path, ".cloudConfigNoActivationRecord")
    cmd = ["/usr/bin/profiles", "-e"]
    run_cmd(cmd)
    if os.path.exists(bad_record) or os.path.exists(no_activation):
        return False
    try:
        with open(good_record, "rb") as f:
            cloudConfigRecord = plistlib.load(f)
    except:
        return False
    if "CloudConfigFetchError" in cloudConfigRecord:
        return False
    return True


def get_logged_in_user():
    """Returns the UID of the current logged in user"""
    user, uid, gid = SCDynamicStoreCopyConsoleUser(None, None, None)
    return user, uid

def run_dialog(dialog):
    """Runs the SwiftDialog app and returns the exit code"""
    jsonString = json.dumps(dialog)
    write_log("running dialog")
    result = subprocess.run([dialogApp, "--jsonstring", jsonString])
    return result

def run_cmd(cmd):
    """Run the cmd"""
    run = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output, err = run.communicate()
    if err:
        write_log(err)
    return output, err

def manage_Admin(init_admin=False, remove=False):
    user_id = get_logged_in_user()
    checkadmin = ["dseditgroup", "-o", "checkmember", "-m", user_id[0], "admin"]
    write_log("checking admin")
    admin = run_cmd(checkadmin)
    if str(admin).find("yes") != -1:
        removeadmin=False
        write_log("Already admin")
        if init_admin == True and remove == True:
            write_log("removing admin")
            removeadmin = ["dseditgroup", "-o", "edit", "-d", user_id[0], "-t", "user", "admin"]
            run_cmd(removeadmin)
    else:
        removeadmin=True
        write_log("promoting to admin")
        makeadmin = ["dseditgroup", "-o", "edit", "-a", user_id[0], "-t", "user", "admin"]
        run_cmd(makeadmin)
    return removeadmin, user_id[1]

def dep_nag(uid):
     depnag = ["/bin/launchctl", "asuser", str(uid), "/usr/bin/profiles", "renew", "-type", "enrollment"]
     run_cmd(depnag)
     write_log("Send dep nag command")

def jamf_check():
    if os.path.exists("/usr/local/jamf"):
        write_log("found Jamf, exiting...")
        return True
    else:
        return False

def main():
    #Check if we are in Jamf
    if jamf_check():
        sys.exit(0)

    # Ensure Swift-Dialog is installed
    write_log("swiftDialog check")
    check = swiftDialog_Check()
    if check[0] == False:
         write_log("swiftDialog install")
         swiftDialog_Install(check[1], check[2])
    
    # send initial dialog
    result = run_dialog(content_base)
    if result.returncode == 2:
        write_log("user deferred")
        content_Defer()
        sys.exit(0)
    elif result.returncode == 0:
        removeadmin, uid = manage_Admin()
        dep_nag(uid)
    else:
         write_log(f"Dialog unexpectedly closed error code: {result.returncode}")    

    # leave dialog and script running until we determine they are enrolled in Jamf.
    i = 0
    while jamf_check() == False and i < 5:
        result = content_step1()
        if result == 2:
            dep_nag(uid)
        elif result == 0:
            pass
        else:
            write_log(f"Dialog unexpectedly closed error code: {result}")
        time.sleep(1) 
        i+=1
    manage_Admin(removeadmin, True)
    if jamf_check():
        content_Complete()
    else:
        content_Defer()

main()
    