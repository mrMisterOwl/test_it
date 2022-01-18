# test_it

- The test script was written using Python version 3.10
- Script was written / tested using a Mac. There are likely code changes that will need to be made in order to run on alternate operating systems 
- Script should be executed with this command: sudo python3 test_it.py
- 'sudo' is included because a .csv file is created in the same directory as the test script.  The .csv file contains test results

The test script follows this process:

  1) checks the script directory for broken-hashserve.tar file.  If it doesnt exist, it connects to amazon s3 and downloads, unpacks the .tar file and installs the .pkg.  
  2) if the .tar file is found, it checks to see if the application is already running by sending a stats request. If so, it shuts it down.  This is so we will know the exact amount of requests sent since start-up while running tests.  
  3) next, the script sets the default port value = 8088
  4) then the script starts the application, waits 10 seconds and then sends a request to stats.  If no response, we assume the app cannot start and we bail.  If response, then we execute tests.
  5) script progress is output to a log in the same directory as the script, executed test results are output to .csv in same directory.


Some warts: 

  1) test 1 should be multi-threading 100 requests to the application, so I expect execution to be fast, but it isnt.  Not sure if the application is throttled somehow or if I messed up my multi-treading code. 
  2) test 9 kept barfing and killing the script, so I commented it out.
  3) a couple of tests output curl command responses to the terminal during execution, which is confusing and annoying altho it doesnt mess up test execution.  I tried to pass a -s in the curl commands to silence, but that didnt do the trick.  
  4) one test that i didnt get around to writing was sending a shutdown command while many hash requests were executing to test that the app stops accepting requests.  I'm just too tired at this point.  :-). 
  5) I know that I should have created a test class so that I could just create new test class objects rather than defining the same variables each time I defined a new test.  
