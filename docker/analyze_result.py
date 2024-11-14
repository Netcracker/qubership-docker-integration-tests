from datetime import datetime
from enum import Enum
import logging

from robot.api import ExecutionResult
from robot.model import TestSuite

space = "\n**********************************************************************************************************\n"

class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"

def analyze_result():
    try:
        result = ExecutionResult("./output/output.xml")
    except Exception as e:
        logging.error("Exception occurred while open tests result file: {}".format(str(e)))
        return

    logging.debug("Start parsing the robotframework test result")
    file_write = open('./output/result.txt', 'w')
    main_suite = result.suite
    result_str = "Main Test Suite: {}\t|\tPassed: {}\t|\tFailed: {}\n".format(main_suite.name,
                                                                              main_suite.statistics.passed,
                                                                              main_suite.statistics.failed)
    if main_suite.suites:
        result_str += space
        result_str += print_suite(main_suite.suites)
    result_str += space
    if main_suite.status == Status.FAIL:
        result_str += "RESULT: TESTS FAILED\n"
    else:
        result_str += "RESULT: TESTS PASSED\n"
    file_write.write(result_str)
    file_write.close()
    logging.debug("The result file has been saved")


def get_keywords(entity):
    keywords = []
    if entity.has_setup:
        keywords.append(entity.setup)
    if not isinstance(entity, TestSuite):
        keywords.extend(entity.body.filter(keywords=True))
    if entity.has_teardown:
        keywords.append(entity.teardown)
    return keywords


def print_test_cases(test_cases, level=0):
    result_str = ""
    for test_case in test_cases:
        start_time = datetime.strptime(test_case.starttime, "%Y%m%d %H:%M:%S.%f")
        end_time = datetime.strptime(test_case.endtime, "%Y%m%d %H:%M:%S.%f")
        duration = int((end_time - start_time).total_seconds() * 1000) # Total time in milliseconds
        result_str += "{}{}\t|\tStatus: '{}'|\tDuration: {}\n".format("\t" * level, test_case.name, test_case.status, duration)
        if test_case.status != Status.PASS:
            keywords = get_keywords(test_case)
            if keywords:
                result_str += "{}Keywords:\n".format("\t" * level)
                result_str += print_keywords(keywords, level + 1)
        result_str += "\n"
    return result_str


def print_keywords(keywords, level=0):
    result_str = ""
    for keyword in keywords:
        result_str += "{}{}\t|\tStatus: '{}'\n".format("\t" * level, keyword.kwname, keyword.status)
        if keyword.status == Status.FAIL:
            if keyword.messages:
                result_str += "{}Messages:\n".format("\t" * level)
                result_str += print_messages(keyword.messages, level + 1)
            nested_keywords = get_keywords(keyword)
            if nested_keywords:
                result_str += "{}Keywords:\n".format("\t" * level)
                result_str += print_keywords(nested_keywords, level + 1)
    return result_str


def print_messages(messages, level=0):
    result_str = ""
    for message in messages:
        result_str += "{}{}\t|\tLevel: '{}'\n".format("\t" * level, message.message.replace("\n", ""), message.level)
    return result_str


def print_suite(suites):
    result_str = ""
    for suite in suites:
        result_str += "Suite: {}\t|\tPassed: {}\t|\tFailed: {}\n".format(suite.name,
                                                                         suite.statistics.passed,
                                                                         suite.statistics.failed)
        keywords = get_keywords(suite)
        if keywords:
            result_str += "Keywords:\n"
            result_str += print_keywords(keywords, 1)
        if suite.tests:
            result_str += "Test cases:\n"
            result_str += print_test_cases(suite.tests, 1)
        if suite.suites:
            result_str += print_suite(suite.suites)
            result_str += space
    return result_str


analyze_result()
