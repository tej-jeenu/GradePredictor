from os import error
from re import match
from flask import Flask, render_template, url_for, request, redirect
import random
import smtplib
import sqlite3
import string
import bcrypt
from flask.sessions import NullSession
from matplotlib.pyplot import psd
import numpy

#https://stackoverflow.com/questions/39772670/flask-return-multiple-variables use this to return stuff
app = Flask(__name__)
studentstatus = ""
teacherstatus = ""
valid = False
salt = bcrypt.gensalt()


def rangecheck(value, minlim, maxlim):
    try:
        value = float(value) # if the value can be made as a float we know the value is a number or a float
    except:
        output = '<p> error some fields were empty or not entered in correct format, please try again :( </p>'
    else:
        if(value >= minlim and value <= maxlim): # if the value is a number we then need to check if the value is in the right range
            output = ""
        else:
            output = '<p> grade averages or dates entered within incorrect range :( </p> '
    
    return output

def numcheck(value):
    try:
        value = float(value) #here it is checking if I can conver the input into a float, if yes we know the input is a number
    except:
        output = "<p> error some fields were empty or not entered in correct format, please try again :( </p>"
    else:
        output = ""
    return output

def emptycheck(value):
    output = "" 
    if(value == ""): # if its empty we know that no data was added"
        output = "<p> a required field was left empty or data wasn't added to display information:( </p>"
    return output

def pointsystem(grade):
    points = 0
    if(grade == "A*"):
        points = 60   # since we can't plot letters as points
    if(grade == "A"): # I used a number system adopted by my school
        points = 50   # to convert the letter grade to number
    if(grade == "B"):
        points = 40
    if(grade == "C"):
        points = 30
    if(grade == "D"):
        points = 20
    if(grade == "E"):
        points = 10
    if(grade == "F" or grade == "G" or grade == "U"): # since there are all failing grades they aren't worth any value hence 0
        points = 0
    return points

def gradesystem(points):
    points = float(points) 
    grade = "" 
    if(points < 10):
        grade = "U"     # In this case need to use one of the failing grades for conversion to work right
    if(points >= 10):   # To output a letter grade I need to convert the float version of the grade
        grade = "E"     # from the regression model into a letter grade
    if(points >= 20):
        grade = "D"
    if(points >= 30):
        grade = "C"
    if(points >= 40):
        grade = "B"
    if(points >= 50):
        grade = "A"
    if(points >= 60):
        grade = "A*"
    return grade

def createfirstmodel(normarray, shiftarray, agrd, subject):
    alev = pointsystem(agrd)
    dep = getalevdepavg(subject)
    standev = numpy.std(shiftarray)
    regressionmodel = numpy.poly1d(numpy.polyfit(normarray, shiftarray, 2))
    
    diff = dep - alev  # here I am using standard deviation to factor in a level department average
    shift = (diff/60) * standev
    regressionmodel = regressionmodel + shift #the purpose of this is to shift exactly based on how big the differenct in the ranges of standard deviatioregressionmodel = regressionmodel + shift

    return regressionmodel

def outofrangetightcheck(x, y, countershift, xval):
    counter = 0
    rangediff = max(x) - min(x)
    if(xval < min(x)):
        while(xval < min(x)):
            xval = xval + countershift
            counter = counter + 1
    else:
        counter = 0
            
    if(xval > max(x)):
        yval = max(y)
    else:
        percentile = ((xval - min(x))/rangediff) * 100
        yval = numpy.percentile(y, percentile)
        yval = yval - (counter * 5)
    
    return yval 

def standev(array): # I attempted using this but stuck with the built in function as my aim is to be as accurate as possible
    total = 0       # It worked when testing but felt that the bult in function most likely to a better degree of accuracy
    meanofsquares = 0
    
    for num in array:   # standard deviation is doing the mean of the squares minus the square of the mean
        total = total + num

    mean = float(total/len(array)) # mean could be a decimal therefore I said it could be a float

    for num1 in array:
        meanofsquares = meanofsquares + (num1 ** 2)
    
    standev = (meanofsquares - (mean ** 2))**0.5 # formula = mean of the squares - square of mean as a formula square rooted
    return standev

def outlierremoval(array1, array2):
    arr1 = []
    arr2 = []
    arr1 = list(array1)
    arr2 = list(array2)

    q1 = numpy.percentile(array1, 25) # we want to find the vlaue at the 25th and 75th percential for lower and 
    q3 = numpy.percentile(array1, 75) # upper quartile 
    i = 0

    outliertype1 = q1 - (1.5*(q3-q1)) # outlier formula
    outliertype2 = q3 + (1.5*(q3-q1))

    for item in arr1:
        #item = float(item)
        if(item <= outliertype1):
            arr1.remove(item)
            arr2.remove(array2[i])
        elif(item >= outliertype2):
            arr1.remove(item)
            arr2.remove(array2[i])
        i = i + 1

    return arr1, arr2

    # here i will use percentiles to idenitfy outliers 

def authourisationcheck():
    errorstatement = ""
    conn = sqlite3.connect(client + '.db')
    c = conn.cursor() # if a teacher isn't logged in to this database then a student must be logged in
    
    c.execute("SELECT status1 FROM teacherstatus")
    teacherstatus = c.fetchall()
    teacherstatus = formatdata(teacherstatus)

    if teacherstatus == "false": # if a certain feature is locked for students then they shouldn'tbe able to access it
        errorstatement = "<p> (^) feature locked for students </p>"

    return errorstatement

def statusauthorisationcheck():
    appexit = ""
    conn = sqlite3.connect(client + ".db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS studentstatus(status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS teacherstatus(status1 TEXT)")
    # here i'm creating tables to track whos currently using the school account
    c.execute("SELECT status FROM studentstatus")
    studentstatus = c.fetchall()
    studentstatus = formatdata(studentstatus)
    
    c.execute("SELECT status1 FROM teacherstatus")
    teacherstatus = c.fetchall()
    teacherstatus = formatdata(teacherstatus)

    if(studentstatus == ""): # If a user has signed up for the first time no one would've logged in before
        c.execute("INSERT INTO studentstatus VALUES('0')")
        studentstatus = "0"
    if(teacherstatus == ""):
        c.execute("INSERT INTO teacherstatus VALUES('false')")
        teacherstatus = "false"
    
    if(teacherstatus == "true"):
        appexit = "teacher"   # if a teacher is using the account no other student or teacher can log in 
    else:                     # anyone else attempting to log in if this case true therefore has to immediately be indicated as follows
        if(usertype == "teacher"):
            if(teacherstatus == "false" and studentstatus == "0"):
                teacherstatus = "true"  # if no other teacher or student is using the account the student can log in 
                c.execute("UPDATE teacherstatus SET status1 = (?)",(teacherstatus,))
            if(int(studentstatus) > 0):
                appexit = "student"  # if a a teacher tries to log in but  one or more students is using it then a teacher has to be indicated
        if(usertype == "student"):
            studentstatus = int(studentstatus)  
            studentstatus = int(studentstatus) + 1 # as long as no teacher is using it the number of student will keep incrementing by 1 as more students log in
            studentstatus = str(studentstatus)
            c.execute("UPDATE studentstatus SET status = (?)",(studentstatus,))
    conn.commit()
    return appexit

def formatdata(content):
    content = str(content)
    for char in ",'()[]": # when retrieving data from a database, there is extra information e.g. brackets
        content = content.replace(char,'') # which does not need to be printed therefore this subroutine will remove extra unecessary character
    return content 

def Astarcase(subject):
    departmentaverage = getalevdepavg(subject)
    points = 60 
    if(departmentaverage <= 50):
        points = points + 5   # department average will affect the liklihood of the A*
    if(departmentaverage > 50 and departmentaverage < 60):
        points = points + 7
    return points

def getalevdepavg(subject):
    conn = sqlite3.connect(client + '.db')
    c = conn.cursor()
    c.execute("SELECT ALevelDepartmentAverage FROM departmentaverages WHERE subject = (?) ",(subject,))
    dep = c.fetchall()
    dep = formatdata(dep) # this is done to retrieve the saved department averages from a table
    dep = float(dep)
    return dep


@app.route('/', methods = ["POST", "GET"])
def createpage():
    if request.method == "POST":
        conn = sqlite3.connect('logindata.db')
        c = conn.cursor()
        user = request.form["usr"]
        usern = request.form["usrn"] # here all the details are collected
        passw = request.form["psd"]
        usertype = request.form.get("usrtype")

        if (request.form.get("verified") == "sentver"):
             v1 = random.randint(0,9)
             v2 = random.randint(0,9)
             v3 = random.randint(0,9)
             v4 = random.randint(0,9)
             
             message = str(v1) + str(v2) + str(v3) + str(v4)
             server = smtplib.SMTP("smtp.gmail.com", 587)
             server.starttls()   # this library will send a message from a gmail account to a user to verify their identity
             server.login("predictgrade@gmail.com", "NEAtest123")
             server.sendmail("predictgrade@gmail.com", user, message)
             
             c.execute("CREATE TABLE IF NOT EXISTS verificationcodes(code TEXT, email TEXT)")

             c.execute("SELECT code FROM verificationcodes WHERE email = (?)", (user,))
             matches = c.fetchall() # this is done to retrieve the email linked to the verification code 
             matches = formatdata(matches)

             if(matches != ""): # if the same user sends another verification it has to replace the previous verification code
                c.execute("UPDATE verificationcodes SET code = (?) WHERE email = (?)" ,(message, user))
             if(matches == ""): # if the verification code doesnt already exist it is added to the table to then create the account
                c.execute("INSERT INTO verificationcodes(code, email) VALUES (?,?)",(message, user))

             conn.commit()

             return render_template('loginpage.html')

        if(request.form.get("submit") == "checkforsubmission"):
             code = request.form["verificationcode"]

             output = emptycheck(usern)
             if(output != ""):
                    return output
        
             output = emptycheck(passw)
             if(output != ""):
                   return output

             c.execute("SELECT email FROM verificationcodes WHERE code = (?)", (code,))
             emailassoc = c.fetchall() # to retrieve the email linked to the code entered provided it existed in the verification table
             emailassoc = formatdata(emailassoc)
             conn.commit()

             if(emailassoc != ""):
                 c.execute("DELETE FROM verificationcodes WHERE email = (?)", (emailassoc,))
                 conn.commit()
                 finalpassw = passw.encode("utf-8")
                 hashedpw = bcrypt.hashpw(finalpassw, salt) # hashing with a salt takes place here
                 c.execute("CREATE TABLE IF NOT EXISTS logindetails(usernames TEXT, emails TEXT, passwords TEXT, usertype TEXT)")
        
                 c.execute("SELECT emails FROM logindetails WHERE emails = (?)",(emailassoc,))
                 emails = c.fetchall() # since you cant have the same email as someone else, it needs to be checked
                 emails = formatdata(emails)

                 if(emails != ""):
                    return render_template('loginpage.html')
            
                 c.execute("INSERT INTO logindetails(usernames, emails, passwords, usertype) VALUES (?,?,?,?)",(usern, emailassoc, hashedpw, usertype))
                 conn.commit()
             return render_template('loginpage.html')  
    else:
        return render_template('loginpage.html')

@app.route('/login', methods = ["POST", "GET"])
def loginpage():
    if request.method == "POST":
        global valid
        global usertype
        found = False

        conn = sqlite3.connect('logindata.db')
        c = conn.cursor()

        user = request.form["usr"]
        passw = request.form["psd"].encode("utf-8")

        c.execute("SELECT emails FROM logindetails")
        emails = c.fetchall()
        for matches in emails: 
            matches = formatdata(matches) # since you cant have the same email as someone else, it needs to be checked
            if(matches == user):
                found = True  # we want to find the user type based on the user to allow certain features
                c.execute("SELECT usertype FROM logindetails WHERE emails = (?) ",(user,))
                usertype = c.fetchall()
                usertype = formatdata(usertype)
        
        if(found == True):
            global client

            c.execute("SELECT passwords FROM logindetails WHERE emails = (?)",(user,))
            correctpassword = c.fetchall() # this is the actual password associated with the username
            correctpassword = str(correctpassword)
            for char in ",'()":
                correctpassword = correctpassword.replace(char,'')

            correctpassword = correctpassword[2:62]  # this is done to extract the relevant hash
            correctpassword = correctpassword.encode("utf-8")

            c.execute("SELECT usernames FROM logindetails WHERE emails = (?)",(user,))
            client = c.fetchall()
            client = formatdata(client)
            
            # since a pepper was used, every ascii character needs to be checked
            if bcrypt.checkpw(passw, correctpassword):
                valid = True

        if(valid == True):
            valid = False 
            statusupdate = statusauthorisationcheck()
            if(statusupdate == "student"): #this is to indicate the reason behind why the user can't log in 
                return '<p> Students are currently predicting or updating their grades, please wait... </p>'
            if(statusupdate == "teacher"):
                return '<p> a Teacher is currently predicting or updating their grades, please wait... </p>'
            else:
                return render_template('homepage.html', person = client, usertype = usertype)

        return render_template('loginpagetwo.html')
    else:
        return render_template('loginpagetwo.html')

@app.route('/home')
def homepage():
    return render_template("homepage.html", person = client, usertype = usertype)

@app.route('/departmentaverage', methods = ["POST", "GET"])
def dep_avgpage():
    errorstatement = authourisationcheck()
    if(errorstatement != ""):
        return errorstatement
    if request.method == "POST":
        authourisationcheck()
        conn = sqlite3.connect(client + '.db')
        c = conn.cursor()

        sub = request.form.get("subject")
        departmentavg = request.form["alevdepavg"]

        errorstatement = rangecheck(departmentavg, 0, 60) # the department average has to be between 0 and 60
        if(errorstatement != ""):
            return errorstatement 

        c.execute("CREATE TABLE IF NOT EXISTS departmentaverages(Subject TEXT, ALevelDepartmentAverage TEXT)")
        c.execute("SELECT ALevelDepartmentAverage FROM departmentaverages WHERE subject = (?) ",(sub,))
        updatestatus = c.fetchall()  # this is done to see whether the value needs to be updated or newly added
        updatestatus = formatdata(updatestatus) # this works correctly no alteration needed
        

        if(updatestatus == ""): # if this subject's department average hasn't been entered before then this command has to be used
            c.execute("INSERT INTO departmentaverages(Subject, ALevelDepartmentAverage) VALUES (?,?)",(sub, departmentavg))
        else:
            c.execute("UPDATE departmentaverages SET ALevelDepartmentAverage = (?) WHERE Subject = (?)" ,(departmentavg, sub))
            # since there is the possibility that the department average of subject has changed, the department average has to be updated instead of adding another entry with the same subject
        conn.commit()

        return render_template("departmentavg.html", person = client)
    else:
        return render_template("departmentavg.html", person = client)

@app.route('/data', methods = ["POST", "GET"])
def data_contributionpage():
    errorstatement = authourisationcheck()
    if(errorstatement != ""):
        return errorstatement
    if request.method == "POST":
        conn2 = sqlite3.connect(client +'.db')
        c2 = conn2.cursor()
        Agrd = request.form.get("alevpredgrd")
        Agrd2 = request.form.get("alevgrd")  #options from the dropdown menus are entered into database
        gcsegrd = request.form.get("gcsegrd")
        sb = request.form.get("sub") # here I am using short variable names to make it easy to write code
        ga = request.form["gcseavg"]

        errorstatement = rangecheck(ga, 1, 9)
        if(errorstatement != ""):
            return errorstatement 

        rt = request.form.get("revtechnique")
        c2.execute("CREATE TABLE IF NOT EXISTS regressionmodel(subject TEXT, GCSEgrade TEXT, ALevelpredictedgrade TEXT, ALevelgrade TEXT, GCSEaverage TEXT, Revisiontechnique TEXT)")
        c2.execute("INSERT INTO regressionmodel(subject, GCSEgrade, ALevelpredictedgrade, ALevelgrade, GCSEaverage, Revisiontechnique) VALUES (?,?,?,?,?,?)",(sb, gcsegrd, Agrd, Agrd2, ga, rt))
        c2 = conn2.cursor() # creates or adds to the table which holds the regression model data
        conn2.commit()
        return render_template('Datacontributionpage.html', person = client)
    else:
        return render_template('Datacontributionpage.html', person = client)

@app.route('/predict', methods = ["POST", "GET"])
def predict():
    if request.method == "POST":
        gcselist = []
        alevellist=[]
        alevelpredlist = []
        valid = True
        global col
        global explanation
        global sbpredicted
        highcasexception = False
        tightcasexception = False
        i = 0
        conn2 = sqlite3.connect(client + '.db')
        c2 = conn2.cursor()

        x_axis = []
        y_axis = []
        x_axis2 = []
        y_axis2 = []

        Agrd = request.form.get("alevpredgrd")  #options from the dropdown menus are entered into database
        gcsegrd = request.form.get("gcsegrd")
        sbpredicted = request.form.get("sub") # here I am using short variable names to make it easy to write code
        ga = request.form["gcseavg"]
        rt = request.form.get("revtechnique")
        st = request.form["studentid"]  # im making variable names short so that declaring is easy
        co = request.form.get("currentorder")

        errorstatement = numcheck(st)
        if(errorstatement != ""):
            return errorstatement 

        errorstatement = rangecheck(ga, 1, 9)
        if(errorstatement != ""):
            return errorstatement 
        
        c2.execute("SELECT GCSEgrade FROM regressionmodel WHERE subject = (?) ",(sbpredicted,))
        gcsegradestuff = c2.fetchall()
        gcsegrades = formatdata(gcsegradestuff)

        errorstatement = emptycheck(gcsegrades) # since we know all data entered has to be entered at the same time 
        if(errorstatement != ""):                        # if data wasn't present for one field then no data had to be present for other fields
            return errorstatement 
        
        c2.execute("CREATE TABLE IF NOT EXISTS studentprogress(student TEXT, subject TEXT,  recentordergrade TEXT, estimatedgrade TEXT)")

        c2.execute("SELECT estimatedgrade FROM studentprogress WHERE student = (?) AND subject = (?)", (st, sbpredicted))
        potentialduplicate = c2.fetchall()
        potentialduplicate = formatdata(potentialduplicate)

        if(potentialduplicate != ""):
            return "<p> this student's data was already entered </p>"
        
        if(Agrd == "A*" and gcsegrd == "9" and float(ga) > 8.7):
            highcasexception = True

        for item in gcsegradestuff:
            grade = str(item)
            grade = grade[2:3]
            grade = float(grade)
            gcselist.append(grade)
        
        # getting data for x axis 
        c2.execute("SELECT GCSEaverage FROM regressionmodel WHERE subject = (?) ",(sbpredicted,))
        gcseaveragestuff = c2.fetchall()
        for item in gcseaveragestuff:
            gradeaverage = formatdata(item)
            gradeaverage = float(gradeaverage)
            gcsetotal = (90/100 * gcselist[i]) + (10/100 * gradeaverage)
            x_axis.append(gcsetotal)
            i = i + 1
        
        # y axis stuff and stuff for graph 2
        i = 0

        c2.execute("SELECT ALevelgrade FROM regressionmodel WHERE subject = (?) ",(sbpredicted,))
        alevelgradestuff = c2.fetchall()
        for item in alevelgradestuff:
            alev = formatdata(item)
            alevellist.append(pointsystem(alev))
        
        y_axis = alevellist
        y_axis2 = alevellist
        
        c2.execute("SELECT ALevelpredictedgrade FROM regressionmodel WHERE subject = (?) ",(sbpredicted,))
        alevelpredstuff = c2.fetchall()
        for item in alevelpredstuff:#points = pointsystem(alevellist[i])
            alpred = formatdata(item) # this is repsonsible for removing any error related things
            alevelpredlist.append(pointsystem(alpred))
            i = i + 1
            
        x_axis2 = alevelpredlist

        import numpy
        import matplotlib.pyplot as plt
        from sklearn.metrics import r2_score

        x = x_axis
        y = y_axis
        x2 = x_axis2
        y2 = y_axis2
         
        x, y = outlierremoval(x, y) # I made a function to remove outliers to prevent the data being skewed
        y, x = outlierremoval(y, x)

        x2, y2 = outlierremoval(x2, y2)
        y2, x2 = outlierremoval(y2, x2)

        minGCSEval = min(x_axis) # this is done to get the minimum value to plot a curve from as the 
        minApredval = min(x_axis2) # this is because a quadratic could be increasing in the opposite end if nto specified correctly
        # in this unlikely case the predicted values have to be between these two values so theres no point of plotting regression model

        #return str(x) + " " + str(y) + " " + str(x2) + " " + str(y2)

        regressionmodel2 = numpy.poly1d(numpy.polyfit(x2, y2, 2))
        regressionmodel1 = createfirstmodel(x,y, Agrd, sbpredicted)
        
        # this sectio of code is in case the data is packed together tightly
        if((max(y) - min(y) <= 10)):
            tightcasexception = True

            xvaltight1 = (90/100 * float(gcsegrd)) + (10/100 * float(ga))
            xvaltight2 = pointsystem(Agrd)

            yvaltight1 = outofrangetightcheck(x,y,1,xvaltight1)
            yvaltight2 = outofrangetightcheck(x2,y,10,xvaltight2)
            
            if(xvaltight2 > max(x2)):
                shift2 = yvaltight2 - max(x2)
            else:
                shift2 = yvaltight2 - pointsystem(Agrd)

            alev = pointsystem(Agrd)
            dep = getalevdepavg(sbpredicted)
            standev = numpy.std(y)

            diff1 = dep - alev  # here I am using standard deviation to factor in a level department average
            shift3 = (diff1/60) * standev  #the purpose of this is to shift exactly based on how big the differenct in the ranges of standard deviatioregressionmodel = regressionmodel + shift
              # need to update this by reading from database 
      
        myline = numpy.linspace(minGCSEval, 9)   #this is responsible for getting the data for making the trend
        plt.scatter(x, y)
        plt.plot(myline, regressionmodel1(myline))
        plt.show()

        mysecondline = numpy.linspace(minApredval, 60)   #this is responsible for getting the data for making the trend
        plt.scatter(x2, y2)
        plt.plot(mysecondline, regressionmodel2(mysecondline))
        plt.show()
        
        yvalnormal1 = regressionmodel1((90/100 * float(gcsegrd)) + (10/100 * float(ga))) # this will take into account aptitude from GCSE to predict likelihood for A-Level Grade
        yvalnormal2 = regressionmodel2(pointsystem(Agrd)) # this will account for how inflated the predicted grades to the actual grades recieved
        shift = yvalnormal2 - pointsystem(Agrd) # this variable is to inflate or deflate the grade based on regressionmodel2
        
        if(highcasexception == True):
            alevgrd = Astarcase(sbpredicted)
        if(tightcasexception == True):
            alevgrd = yvaltight1 + shift2 + shift3
        else:
            alevgrd = yvalnormal1 + shift

        global strgrade #getting the letter equiavlent for the number of points
        strgrade = gradesystem(alevgrd)
        
        alevgrd = str(alevgrd)
        # this section of the code is for determining information to publish on the next page
        num = alevgrd[1:2]
        num = float(num)

        if(num < 4):
            col = "color: red"
            explanation = "Low probability of grade, This student can get this grade but with extra hours of work put in"
        
        if(num >= 4 and num <= 6):
            col = "color: #FFCC00"
            explanation = "This student is likely to achieve this grade with their current methods"
        
        if(num > 6):
            checknum = float(alevgrd)
            if(checknum >= 60):
                 col = "color: green"
                 explanation = "High probability of grade"  
            else:
                col = "color: green"
                explanation = "High probability of grade, The student could even jump the next grade doing more hours of the same revision technique"

        c2.execute("INSERT INTO studentprogress(student, subject, recentordergrade, estimatedgrade) VALUES (?,?,?,?)",(st, sbpredicted, co, strgrade))
        conn2.commit()

        i = 10
        j = 0

        global revisiontechniqueset  # these are variables to hold the information about revision advice
        global gradesabove # this is used to be clear about the specific grade that is aimed to be achieved

        revisiontechniqueset = []
        gradesabove = []
        Listofgrades = ["U","G","F","E","D","C","B","A","A*"] # this list is used to identify the correct order in terms of level
        # the order needs to be position from lowest to highest to allow
        pos = Listofgrades.index(strgrade)
        
        if(pos == len(Listofgrades) - 1):
            pos = Listofgrades.index(strgrade)
        else:
            pos = Listofgrades.index(strgrade) + 1

        while(pos < len(Listofgrades)):
            c2.execute("SELECT Revisiontechnique FROM regressionmodel WHERE ALevelgrade = (?)", (Listofgrades[pos],))
            sample = c2.fetchall()

            j = 0
            i = len(sample) # this works fine to retrieve revision techniques

            while(j < i):
                sample[j] = formatdata(sample[j])
                j = j + 1

            for item in sample:    # this will make sure the currently used revision technique isn't mentioned again 
                   if(item == rt): # as this won't be useful to the usw
                       sample.remove(item)


            sample = list(dict.fromkeys(sample)) # this will remove anything repeatedy mentioned 
            revisiontechniqueset.append(sample)  # if it's mentioned again for a specific grade

            gradesabove.append(Listofgrades[pos])
            pos = pos + 1
        #alevgrd = float(alevgrd)

        # I need to test the retrieval of the revision techniques in a seperate place
        # this is an array of all the revision techniques for the specific grade 
        # I need to add an array within positions in an array 

        if(valid == True):
            return render_template('predictionanalysispage.html', colour = col, len = len(gradesabove), grade = strgrade, rank = col, above = gradesabove, exp = explanation, set = revisiontechniqueset )


        return render_template('predictionpage.html', person = client)
    else:
        return render_template('predictionpage.html', person = client)

@app.route('/progress', methods = ["POST", "GET"])
def progress():
    errorstatement = authourisationcheck()
    if(errorstatement != ""):
        return errorstatement
    if request.method == "POST":
        from datetime import datetime
        import datetime
        conn2 = sqlite3.connect(client + '.db')
        colours = []
        relevantstudents = []
        underperforming = []
        c2 = conn2.cursor()

        sb = request.form.get('sub')
        et = request.form.get('estimatedgrd')
        ed = request.form['examdate']
        now = datetime.datetime.now()

        if(now.month < 9):
            mindate = now.year
        else:
            mindate = now.year + 1

        errorstatement = rangecheck(ed, mindate, now.year + 2)
        if(errorstatement != ""):
            return errorstatement 

        if request.form.get('opengrade') == 'gradepressed':
            c2.execute("SELECT student FROM studentprogress WHERE subject = (?) AND estimatedgrade = (?) ",(sb, et))
            students = c2.fetchall()

            for student in students:
                student = formatdata(student)
               
                c2.execute("SELECT recentordergrade FROM studentprogress WHERE student = (?)",(student,))
                grd = c2.fetchall()
                grd = formatdata(grd) # grade conversion is taking place here
                grd = pointsystem(grd)
                estimate = pointsystem(et)

                start = datetime.datetime(now.year, now.month, now.day)
                end = datetime.datetime(int(ed), 6, 15)
                numofmonths = (end.year - start.year) * 12 + (end.month  - start.month )
                progression = ((10/9)*numofmonths) # if we assume by default a student makes a single grade progression throughout the year 
                # this is for heavy underperformance

                if(round(grd + progression) >= estimate - 1):
                    relevantstudents.append(student)
                    colours.append('color: green')      # if the point gap between the grades are a certain amount then it will determines the progress 
                if(round(grd + progression) <= estimate - 20): # of the student
                    underperforming.append(student)
                else:
                    if(round(grd + progression) < estimate - 1):
                        relevantstudents.append(student)
                        colours.append('color: #FFCC00')

            return render_template("studentgradeanalysis.html", len1 = len(relevantstudents), ontargetstudents = relevantstudents, len2 = len(underperforming), underperformingstudents = underperforming, colour = colours)

        if request.form.get('openfull') == 'fullpressed':
            i = 0

            grades = ['A*','A','B','C','D','E','F','G','U'] # these are all the grades
            frequency = []
            finalarray = []

            for grade in grades:
                count = 0
                c2.execute("SELECT student FROM studentprogress WHERE subject = (?) AND estimatedgrade = (?) ",(sb, grade))
                students = c2.fetchall() # this section of code determines the frequency of the people for each grade
                for student in students:
                    count = count + 1
        
                frequency.append(count) 
                i = i + 1

            colors = ['color: green','color: green','color: orange','color: orange','color: #FFCC00','color: #FFCC00','color: red','color: red','color: red']
            # this is a dictionary for all the colours to be formatted into HTML easily
            i = 0
            bar = ""
            for grade in grades:
                bar = ""
                for j in range (0, frequency[i]):
                    bar = bar + "+" # this is to display the count in a visual format by typing a certain number of pluses based on the number of people for each grade
                combinedstring = grade + " " + str(frequency[i]) + " " + bar
                finalarray.append(combinedstring)
                i = i + 1
    
            return render_template("graphlayout.html", stats = finalarray, len = len(grades), colors = colors)
    else:
        return render_template("studentprogresspage.html", person = client)

@app.route('/updateprogress', methods = ["POST", "GET"])
def updateprogress():
    if request.method == "POST":
        conn2 = sqlite3.connect(client + '.db')
        c2 = conn2.cursor()
        
        sb = request.form.get("sub")
        og = request.form.get("recentorder")
        si = request.form["studentid"]

        errorstatement = numcheck(si)
        if(errorstatement != ""):
            return errorstatement

        c2.execute("UPDATE studentprogress SET recentordergrade = (?) WHERE subject = (?) AND student = (?)" ,(og, sb, si))
        conn2.commit()  # this to update a students grade for a specific user and since one user will do multiple subjects, the subject will factor in as well
        
        return render_template("updategradepage.html")
    else:
        return render_template("updategradepage.html")

@app.route('/confirmcomplete', methods = ["POST", "GET"])
def confirmprocessing():
    if request.method == "POST":
        conn = sqlite3.connect(client + ".db")
        c = conn.cursor()

        c.execute("SELECT status FROM studentstatus")
        studentstatus = c.fetchall() # get the current status of students here
        studentstatus = formatdata(studentstatus)
        
        c.execute("SELECT status1 FROM teacherstatus")
        teacherstatus = c.fetchall() # get the current status of teachers here
        teacherstatus = formatdata(teacherstatus)

        if(int(studentstatus) > 0): # this is determining if at least one student is logged in 
            studentstatus = int(studentstatus) 
            studentstatus = studentstatus - 1 # is the user is a student and wants to logout we want to decrement the count of students currently on the system by 1
            studentstatus = str(studentstatus)
        
        if(teacherstatus == "true"): # if a teacher is logging out, we need to make the teacherstatus false as we need to indicate to other school users that a teacher isn't logged in anymore
            teacherstatus = "false"
            
        c.execute("UPDATE studentstatus SET status = (?)",(studentstatus,)) # updating the new status here
        c.execute("UPDATE teacherstatus SET status1 = (?)",(teacherstatus,))

        conn.commit()
        return render_template("loginpage.html")
    else:
        return render_template("confirmationpage.html")

if(__name__ == '__main__'):
    app.run(debug = True)
    app.run(host="192.168.0.13")


  





