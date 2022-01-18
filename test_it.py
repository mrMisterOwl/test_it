import concurrent
import csv
import json
import logging
import random
import string
import time
import xlrd
import subprocess
import os
import datetime
import wget
import requests
import hashlib
import base64
from concurrent.futures import ThreadPoolExecutor

default_port = "8088"
url_prefix = "http://127.0.0.1:"
tar_file = "broken-hashserve.tar"
url_to_app_package = "https://qa-broken-hashserve-jc.s3.amazonaws.com/%s" % tar_file
header = "applications/json"


def config_logging(file):
    file_name = os.path.join(os.getcwd(), "%s.log" % file)
    if os.path.exists(file_name):
        subprocess.run(["rm", file_name])
    logging.basicConfig(filename=file_name,
                        level=logging.DEBUG,
                        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    print("Logging for this test run can be found in: %s" % file_name)


def set_up_test_env():
    if not os.path.exists(os.path.join(os.getcwd(), tar_file)):
        logging.info("Application package not found, getting latest version of hash server at %s ..." % url_to_app_package)
        print("Application package not found, getting latest version of hash server at %s ..." % url_to_app_package)
        get_latest = wget.download(url_to_app_package)
        logging.info(get_latest)
        logging.info("Unpacking .tar file ...")
        untar_file = subprocess.run(['tar', '-xvf', tar_file])
        logging.info("Installing application ... ")
        install_app = subprocess.run(['installer', 'broken-hashserve/broken-hashserve.pkg', '-target', '/'])
    else:
        logging.info("Application is already installed.")
        print("Application is already installed.")
        is_running = subprocess.run(['curl', url_prefix+default_port+"/stats"], capture_output=True, text=True)
        if not is_running.stderr.__contains__("Connection refused"):
            logging.info("Application is running. Will shut down and restart.")
            print("Application is running. Will shut down and restart.")
            data = 'shutdown'
            shut_down = subprocess.run(['curl', '-X', 'POST', '-d', data, url_prefix+default_port+"/hash"], capture_output=True, text=True)
            time.sleep(10)
        else:
            logging.info("Application is not running, starting.")
            print("Application is not running, starting.")
    logging.info("setting default port ...")
    set_port = os.environ["PORT"] = "8088"
    logging.info("Starting application and confirming ...")
    start_app = subprocess.Popen(['broken-hashserve'])
    time.sleep(10)
    is_running = subprocess.run(['curl', url_prefix+default_port+"/stats"], capture_output=True, text=True)
    if str(is_running).__contains__("Connection refused"):
        logging.info("Application failed to start. Exiting test.")
        exit(1)
    else:
        logging.info("Application start succeeded. Proceeding with tests ... ")


def execute_tests():
    today = datetime.date.today()
    results_file = "test_results_<today's_date>.csv"
    output_file = open(os.path.join("test_results_%s.csv" % today), 'w+')
    logging.info("Test results will be available in: %s" % results_file)
    print("Test results will be available in: %s" % results_file)
    writer = csv.writer(output_file)
    writer.writerow(['TEST ID', 'DESC', 'EXPECTED', 'ACTUAL', 'STATUS'])
    logging.info("Executing tests ...")
    print("Executing tests ...")
    rapid_fire_requests(writer)
    test_non_standard_port(writer)
    send_put_and_delete_requests(writer)
    send_empty_pw_string(writer)
    send_bad_param_name(writer)
    time_to_job_identifier(writer)
    time_to_hash_at_least_5_seconds(writer)
    pw_hash_produced_correctly(writer)
    send_bad_job_id(writer)
    # hashed_pw_is_decodable(writer)
    get_stats_accepts_no_data(writer)
    stats_returned_as_json(writer)
    test_app_shutdown(writer)


def test_non_standard_port(writer):
    test_id = 2
    print("executing test %s" % test_id)
    desc = "send non-standard port in stats request."
    expected = "application handles non-standard port in gracefully"
    logging.info("executing test %s" % test_id)
    request = subprocess.run(['curl', url_prefix+"/9099/hash"], capture_output=True, text=True)
    if not request.stderr.__contains__("Connection refused"):
        actual = "Expected connection refused, but it was not"
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def send_put_and_delete_requests(writer):
    test_id = 3
    print("executing test %s" % test_id)
    desc = "send put and delete requests."
    expected = "application handles unsupported request types gracefully"
    logging.info("executing test %s" % test_id)
    put_request = subprocess.run(['curl', '-X', 'PUT', url_prefix+default_port+"/hash"], capture_output=True, text=True)
    delete_request = subprocess.run(['curl', '-X', 'DELETE', url_prefix+default_port+"hash/3"], capture_output=True, text=True)
    if put_request.stdout != "PUT Not Supported" or delete_request.stdout != "DELETE Not Supported":
        actual = "At least one request's response value did not match expectations. PUT response = %s.  DELETE response = %s" % (put_request.stdout, delete_request.stdout)
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def send_empty_pw_string(writer):
    test_id = 4.1
    print("executing test %s" % test_id)
    desc = "send empty pw string."
    expected = "application handles empty pw string gracefully"
    logging.info("executing test %s" % test_id)
    data = '{"password": "  "}'
    request = subprocess.run(['curl', '-X', 'POST', '-H', header, '-d', data, url_prefix+default_port+"/hash"], capture_output=True, text=True)
    if request.stdout != "":
        actual = "Request stdout contained a value (%s), indicating acceptance" % request.stdout
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def send_bad_param_name(writer):
    test_id = 4.2
    print("executing test %s" % test_id)
    desc = "send bad param name string."
    expected = "application handles invalid param name string gracefully"
    logging.info("executing test %s" % test_id)
    data = '{" ": "password"}'
    request = subprocess.run(['curl', '-X', 'POST', '-H', header, '-d', data, url_prefix+default_port+"/hash/"], capture_output=True, text=True)
    if request.stdout != "":
        actual = "Request stdout contained a value (%s), indicating acceptance" % request.stdout
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def time_to_job_identifier(writer):
    test_id = 5
    print("executing test %s" % test_id)
    desc = "job identifier should be returned 'immediately' (< 1 second)"
    expected = "job ID returned 'immediately'"
    logging.info("executing test %s" % test_id)
    data = '{"password": "grooveHolmes"}'
    start = time.time()
    request = subprocess.run(['curl', '-X', 'POST', '-H', header, '-d', data, url_prefix+default_port+"/hash"], capture_output=True, text=True)
    finish = time.time() - start
    if request.stdout == "":
        actual = "Request stdout did not contain a job id. Request should have succeeded."
        result = "fail"
    elif finish > 1:
        actual = "Request response not 'immediate' (> 1 second). Elapsed time was: %s seconds" % finish
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def time_to_hash_at_least_5_seconds(writer):
    test_id = 6
    print("executing test %s" % test_id)
    desc = "application should wait 5 seconds before computing hash"
    expected = "application should wait 5 seconds before computing hash"
    logging.info("executing test %s" % test_id)
    data = '{"password": "steadyEddie"}'
    request = subprocess.run(['curl', '-X', 'POST', '-H', header, '-d', data, url_prefix+default_port+"/hash"], capture_output=True, text=True)
    job_id = request.stdout
    elapsed = 0
    start = time.time()
    if request.stdout == "":
        actual = "Request stdout is empty. Request should have succeeded."
        result = "fail"
        writer.writerow([test_id, desc, expected, actual, result])
    else:
        made_hash = False
        while not made_hash:
            find_hash = subprocess.run(['curl', '-s', '-H', header, url_prefix+default_port+"/hash/"+job_id])
            if not find_hash.stdout == "":
                elapsed = time.time() - start
                made_hash = True
        if elapsed < 5:
            actual = "Hash value returned in less than 5 seconds. Actual return was %s seconds" % (time.time() - start)
            result = "fail"
        else:
            actual = "expected"
            result = "pass"
        writer.writerow([test_id, desc, expected, actual, result])


def pw_hash_produced_correctly(writer):
    test_id = 7
    print("executing test %s" % test_id)
    desc = "pw hash should be correctly generated"
    expected = "pw hash value is pw in SHA512 format"
    logging.info("executing test %s" % test_id)
    pw = "flabbergastMe"
    data = '{"password": "flabbergastMe"}'
    expected_hash = hashlib.sha512(str(pw).encode("utf-8")).hexdigest()
    request = subprocess.run(['curl', '-X', 'POST', '-H', header, '-d', data, url_prefix+default_port+"/hash"], capture_output=True, text=True)
    time.sleep(6)
    job_id = request.stdout
    time.sleep(6)
    find_hash = subprocess.run(['curl', '-H', header, url_prefix+default_port+"/hash/"+job_id])
    if not find_hash.stdout == expected_hash:
        actual = "Found hash (%s) doesnt match expected hash (%s)" % (find_hash.stdout, expected_hash)
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def send_bad_job_id(writer):
    test_id = 8
    print("executing test %s" % test_id)
    desc = "Send bad job ID."
    expected = "bad job Id is handled gracefully, doesnt return hash value"
    logging.info("executing test %s" % test_id)
    bad_id = subprocess.run(['curl', '-q', '-H', header, url_prefix+default_port+"/hash/10000"], capture_output=True, text=True)
    if not bad_id.stdout != "Hash not found":
        actual = "Invalid job ID did not return an error"
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def hashed_pw_is_decodable(writer):
    test_id = 9
    print("executing test %s" % test_id)
    desc = "pw hash should be decodable (base64)"
    expected = "pw hash should be decodable (base64)"
    logging.info("executing test %s" % test_id)
    pw = "emulsifier"
    data = '{"password": %s}' % pw
    request = subprocess.run(['curl', '-X', 'POST', '-H', header, '-d', data, url_prefix+default_port+"/hash"], capture_output=True, text=True)
    time.sleep(5)
    job_id = request.stdout
    time.sleep(10)
    find_hash = subprocess.run(['curl', '-H', header, url_prefix+default_port+"/hash/"+job_id])
    hash = find_hash.stdout
    decoded = base64.b64decode(hash)
    if not decoded == pw:
        actual = "Decoded hash (%s) doesnt match original password (%s)" % (decoded, pw)
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def get_stats_accepts_no_data(writer):
    test_id = 10
    print("executing test %s" % test_id)
    desc = "Send data to stats endpoint."
    expected = "Data sent to stats endpoint handled gracefully."
    logging.info("executing test %s" % test_id)
    data = '{"param": "payload"}'
    stats_with_data = subprocess.run(['curl', '-s', '-d', data, url_prefix+default_port+"/stats"])
    if stats_with_data.stderr == "":
        actual = "Stats get request with data payload did not return an error, but should have"
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def stats_returned_as_json(writer):
    test_id = 11
    print("executing test %s" % test_id)
    desc = "Stats response is json format."
    expected = "Stats response is json format."
    logging.info("executing test %s" % test_id)
    stats = subprocess.run(['curl', '-q', url_prefix+default_port+"/stats"])
    try:
        json.loads(stats.stdout)
        actual = "expected"
        result = "pass"
    except:
        actual = "Stats response was not in json format (%s)." % stats.stdout
        result = "fail"
    writer.writerow([test_id, desc, expected, actual, result])


def rapid_fire_requests(writer):
    test_id = 1
    print("executing test %s" % test_id)
    desc = "Send concurrent requests, validate total stats."
    expected = "Application handles concurrent requests and stats shows accurate total and avg. time."
    logging.info("executing test %s" % test_id)
    rev = 0
    total_time = 0
    while rev < 100:
        with ThreadPoolExecutor(max_workers=10) as executor:
            threads = []
            threads.append(executor.submit(send_many_pws_to_app))
            for elapsed in concurrent.futures.as_completed(threads):
                total_time += elapsed.result()
                rev += 1
    stats = subprocess.run(['curl', url_prefix+default_port+"/stats"], capture_output=True, text=True)
    print("stats stdout: %s" % stats.stdout)
    stats_results = json.loads(stats.stdout)
    total_reqs = stats_results["TotalRequests"]
    avg_time = stats_results["AverageTime"]
    if total_reqs != 100:
        actual = "Expected total requests value to be 100, but got %s" % total_reqs
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])
    calc_avg_time = total_time / 100
    if calc_avg_time != avg_time:
        actual = "Expected average time to be %s, but got %s" % (calc_avg_time, avg_time)
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def send_many_pws_to_app():
    itr = 0
    rand_pw = ""
    while itr <= 10:
        rand = random.choice(string.ascii_letters + string.digits)
        rand_pw = rand_pw.join(rand)
        itr += 1
    data = '{"password": %s}' % rand_pw
    start = time.time()
    request = subprocess.run(['curl', '-X', 'POST', '-H', header, '-d', "{\"password\":\""+rand_pw+"\"}", url_prefix+default_port+"/hash"])
    elapsed = time.time() - start
    return elapsed


def test_app_shutdown(writer):
    test_id = 12
    desc = "App shuts down gracefully."
    expected = "App shutdown issues 200 response."
    logging.info("executing test %s" % test_id)
    data = 'shutdown'
    request = subprocess.run(['curl', '-X', 'POST', '-d', data, url_prefix+default_port+"/hash"])
    if request.stdout != "200 Empty Response":
        actual = "Expected shutdown to throw '200 Empty Response' in stdout, but got %s" % request.stdout
        result = "fail"
    else:
        actual = "expected"
        result = "pass"
    writer.writerow([test_id, desc, expected, actual, result])


def main():
    config_logging("test_broken_hashserve")
    set_up_test_env()
    execute_tests()


if __name__ == "__main__":
    main()