import os
import re
import math
import smtplib
import Mollie

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from helpers import apology, apology_payment, login_required, create_ticket
from random import randint
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from http import cookies

# Configure application
app = Flask(__name__)
adminname=""
klantID = 0
klantnaam = "bezoeker"
klantnaam_volledig = ""
admins=["Alex", "Daan"]
bestelling={}
grandtotal={}
klant_array={}   # persoonsgebonden array voor DEZE klant in DEZE sessie

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure Mollie
mollie = Mollie.API.Client()
# live key : mollie.setApiKey('live_zr5PeDE3EP5tmKnrahBpV9qbQByHSV')
mollie.setApiKey('test_jhnyPrWfJJrs5u8bRs9yxpfmAxxzDf')  #  <-- test key

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///festival.db")

''' Cookie experiment '''
# Configure session to use filesystem (instead of signed cookies)
app.secret_key = os.urandom(24)

# Ensure templates are auto-reloaded
# app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route('/set')
def setcookie():
    global name
    resp = make_response(render_template("index.html"))
    resp.set_cookie('user',name)
    return resp

@app.route('/get')
def getcookie():
    global name
    name = request.cookies.get('user')
    return('The user is: ' + name)

''' ----------------- '''


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
def index():
    """Render map"""
    #if not os.environ.get("API_KEY"):
    #    raise RuntimeError("API_KEY not set")
    #return render_template("index.html", key=os.environ.get("API_KEY"))

    if request.method == "POST":
        return render_template("kopen.html")
    else:
        return render_template("index.html", admins=admins)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):

            return apology("must provide username", 403)



        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        print("*** 03 ***")

        # Query database for username
        rows = db.execute("SELECT * FROM admins WHERE naam = :username", username=request.form.get("username"))

        # Ensure username exists and password is correct

        if len(rows) != 1:
            return apology("invalid username and/or password.", 403)

        psw=rows[0]['password']

        if not (psw == request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["naam"]

        # Setting var adminname for passing to admin.html
        global adminname
        global admins

        adminname=rows[0]["naam"]

        # Redirect admin to the admin page
        return render_template("admin_page.html" , adminname=adminname, admins=admins )

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        print("goto to admin login page")
        return render_template("admin_login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    global klantnaam_volledig

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif request.form.get("username") == "no username":
            return apology("nice try  :-)", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM bezoeker WHERE username = :username", username=request.form.get("username"))

        # Ensure username exists and password is correct

        if len(rows) != 1:
            return apology("invalid username and or password.", 403)

        psw=rows[0]['password']

        if not (psw == request.form.get("password")):
            return apology("invalid username and or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["bz_id"]
        cookie = cookies.SimpleCookie()
        cookie["klant"] = session["user_id"]

        # Setting var name for passing to klant_page.html
        name=rows[0]["voornaam"]
        tv=rows[0]["tussenvoegsel"]
        ln=rows[0]["achternaam"]

        klantnaam_volledig = name
        if tv !="":
            klantnaam_volledig += " " + tv
        klantnaam_volledig += " " + ln

        global klantID
        klantID=rows[0]["bz_id"]



        # Redirect admin to the admin page
        return render_template("klant_page.html" , name=name )

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/admin_logged_in", methods=["GET", "POST"])
@login_required
def admin_logged_in():
    global adminname
    return render_template("admin_page.html" , adminname= adminname)

@app.route("/scan")
@login_required
def scan():

    return redirect("/")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


""" ============= Admin-pagina's =================="""

@app.route("/adm_transacties")
@login_required
def adm_transacties():

    rows = db.execute("SELECT * FROM transacties")

    totaalbedrag = 0.0


    for row in rows:
        print("klantID: "+str(row['klantID']))
        client = db.execute("SELECT voornaam, tussenvoegsel, achternaam FROM bezoeker WHERE bz_id = :klantID", klantID = row['klantID'] )

        if client:

            naam = client[0]['voornaam']+" "
            if client[0]['tussenvoegsel'] != None:
                naam += client[0]['tussenvoegsel']+" "
            naam += client[0]['achternaam']

        else:

            naam = '?'

        row['klantnaam'] = naam
        totaalbedrag += math.ceil(float(row['totaalbedrag'])*100)/100

    totaalbedrag = math.ceil(totaalbedrag*100)/100

    return render_template("adm_transacties.html" , rows=rows, grandtotal = totaalbedrag, adminname= adminname, admins=admins)

@app.route("/adm_ticketsoorten")
@login_required
def adm_ticketsoorten():

    rows = db.execute("SELECT * FROM ticketsoorten")

    return render_template("adm_ticketsoorten.html" , rows = rows, adminname= adminname, admins=admins)

@app.route("/adm_klanten")
@login_required
def adm_klanten():


    rows = db.execute("SELECT * FROM bezoeker")

    return render_template("adm_klanten.html" ,  rows = rows, adminname= adminname, admins=admins)

@app.route("/adm_tickets")
@login_required
def adm_tickets():

    return render_template("adm_tickets.html" , adminname= adminname, admins=admins)

@app.route("/adm_ingecheckt")
@login_required
def adm_ingecheckt():

    return render_template("adm_ingecheckt.html" , adminname= adminname, admins=admins)

@app.route("/adm_statistieken")
@login_required
def adm_statistieken():

    return render_template("adm_statistieken.html" , adminname= adminname, admins=admins)


""" ================== Klant-pagina's ================== """

@app.route("/kln_gegevens")
@login_required
def kln_gegevens():

    return null

@app.route("/kln_tickets")
@login_required
def kln_tickets():

    return null

@app.route("/kln_transacties")
@login_required
def kln_transacties():

    return null

@app.route("/kln_kopen", methods=["GET", "POST"] )
@login_required
def kln_kopen():

    global klantID
    global bestelling
    global grandtotal
    global klant_array  # persoonsgebonden array voor DEZE klant in DEZE sessie


    try:
        klantID = session["user_id"]
        print("&& klantID is set to: " + str(klantID))
    except:
        print("&& no klantID ! &&")



    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        rows = db.execute("SELECT * FROM ticketsoorten WHERE tekoop = 'true'")

        grandtotal['klantID'] = 0

        for row in rows:
            veldnaam="ticket" + str(row['tk_id'])
            row['aantal'] = request.form.get(veldnaam)
            if row['aantal'] == '':
                row['aantal'] == 0

            # Check user input
            try:
                temp=float(row['aantal'])
                if temp < 0 :
                    return apology('geen waardes kleiner dan 0 a.u.b.', 406)

                row['totaal'] = math.ceil(float(row['aantal']) * row ['ticketprijs']*100)/100
                row['aantal'] = str(int(row['aantal']))
                grandtotal["klantID"]+=row['totaal']
            except ValueError:
                return apology("Wrong input", 406)


        bestelling=rows
        grandtotal["klantID"]=math.ceil(grandtotal["klantID"]*100)/100

        if grandtotal["klantID"] == 0 :
            return apology("U heeft geen tickets besteld.", 406)


        m = db.execute("INSERT INTO Mollie_order (klantID, bedrag) VALUES (:klantID, :bedrag)", klantID = klantID, bedrag = grandtotal["klantID"])

        session["MollieID"] = m

        print("$$$ m = ", end='')
        print(m)


        # Redirect admin to the admin page
        return render_template("klant_bevestig.html" , name=klantID, tickets=rows, grandtotal=grandtotal["klantID"])

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        rows = db.execute("SELECT * FROM ticketsoorten WHERE tekoop = 'true'")
        return render_template("klant_kopen.html", name=klantID, tickets=rows)


@app.route("/kln_disclaimer", methods=["GET", "POST"] )
@login_required
def kln_disclaimer():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        answer1=request.form.get("answer1")
        answer2=request.form.get("answer2")

        if answer1=="Ja":
            print(str(klantID)+ " ::: "+str(grandtotal["klantID"]))
            return redirect("/kln_betalen")
        elif answer2=="Nee":
            return redirect("/")
        else:
            return render_template("klant_disclaimer.html")


    else:
        return render_template("klant_disclaimer.html")


@app.route("/kln_betalen", methods=["GET", "POST"] )
@login_required
def kln_betalen():

    global payment
    global bestelling
    global grandtotal

    try:
        klantID = session["user_id"]
        print("&& klantID is set to: " + str(klantID))
    except:
        print("&& no klantID ! &&")

    Mollie_ID = session["MollieID"]

    print("$$$ Mollie_ID = ", end='')
    print(Mollie_ID)

    m = db.execute("SELECT bedrag FROM Mollie_order WHERE M_id = :MollieID", MollieID = Mollie_ID)

    print("$.$ m = ", end='')
    print(float(m[0]['bedrag']))

    amount = float(m[0]['bedrag'])

    print(str(klantID)+ " ::: "+str(grandtotal["klantID"]))

    rows = db.execute("SELECT tr_id FROM transacties WHERE tr_id= (SELECT MAX(tr_id) FROM transacties)")

    print("rows transacties : ")
    print(rows)

    #transactieID = str(rows[0]['tr_id'])
    transactieID = '-TEST-'

    payment = mollie.payments.create({
    'amount':      amount,
    'description': 'Betaling FESTIVALTICKETS transactie #' + transactieID + ' door ' + klantnaam_volledig,
    'redirectUrl': 'https://ide50-alexicoo.cs50.io:8080/afrekenen',
    'webhookUrl':  'https://ide50-alexicoo.cs50.io:8080/molliewebhook'
    })



    print('  >>> Payment aangemaakt voor klant met klantID: ' + str(klantID) + ', ten bedrage van: '+ str(amount))

    return redirect(payment.getPaymentUrl())



@app.route("/afrekenen", methods=["GET", "POST"])
@login_required
def afrekenen():

    global klantID
    global bestelling
    global grandtotal
    global klantnaam
    global klantnaam_volledig
    global payment

    payment = mollie.payments.get(payment['id'])

    try:
        klantID = session["user_id"]
        print("&& klantID is set to: " + str(klantID))
    except:
        print("&& no klantID ! &&")

    if payment.isPaid():
        print('Payment received.')
    else:
        print('Payment not received.')
        return redirect('/afrekenen')

    akb = 0  # akb = aantal kaarten besteld

    ticketbatch = []

    for row in bestelling:
        akb += int(row['aantal'])
        for t in range(int(row['aantal'])):
            printed = create_ticket(klantID,row['ticketnaam'],t, klantnaam_volledig)  #t = nummering voor tickets als er meer dan 1 ticket van een bepaalde soort is besteld
            ticketbatch.append(printed)
    print("ticketbatch : ")
    print(ticketbatch)

    """ INSERT the purchase in table transacties """

    result = db.execute("INSERT INTO transacties (klantID, aantal_tickets, totaalbedrag) VALUES(:klantID, :aantal_tickets, :totaalbedrag)",
        klantID = klantID, aantal_tickets = akb, totaalbedrag = grandtotal["klantID"])

    if not result:
        return apology("Database error", 403)

    """ mail the tickets to the customer """

    # Get the emailaddress from the customer

    rows = db.execute("SELECT emailadres FROM bezoeker WHERE bz_id = :klantID", klantID = klantID)

    if not rows:
        return apology("Database error", 403)

    mailadr = rows[0]['emailadres']

    # initiate a secure connection

    email_user = 'kuylkamp2018@gmail.com'
    email_password = 'KuylKuyl2018'
    email_send = mailadr

    subject = 'Tickets KuylKamp Familiefestival'

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = email_send
    msg['Subject'] = subject

    body = 'Beste ' + klantnaam + ","
    body+=  """

    Bij dezen ontvangt u de door u bestelde tickets voor het KuylKamp Familiefestival.
    Gelieve deze tickets uit te printen en mee te brengen naar het Festival.

    Veel plezier op het festival !


    De festival-organisatie.


    """

    msg.attach(MIMEText(body,'plain'))

    for att in ticketbatch:
        filename=att
        attachment  =open(filename,'rb')

        part = MIMEBase('application','octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',"attachment; filename= "+filename)
        msg.attach(part)

    text = msg.as_string()
    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    server.login(email_user,email_password)


    server.sendmail(email_user,email_send,text)
    server.quit()


    return render_template("klant_afgerekend.html", name=klantnaam, tickets=bestelling, grandtotal=grandtotal["klantID"])


""" ================== Gast-pagina's ================== """

@app.route("/kopen", methods=["GET", "POST"] )
def kopen():

    global grandtotal

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        rows = db.execute("SELECT * FROM ticketsoorten WHERE tekoop = 'true'")

        grandtotal["klantID"] = 0

        for row in rows:
            veldnaam="ticket" + str(row['tk_id'])
            row['aantal'] = request.form.get(veldnaam)

            print("row[aantal]")
            print(row['aantal'])

            # Check user input
            try:
                temp=float(row['aantal'])
                if temp < 0 :
                    return apology('geen waardes kleiner dan 0 a.u.b.', 406)

                row['totaal'] = math.ceil(float(row['aantal']) * row ['ticketprijs']*100)/100
                row['aantal'] = str(int(row['aantal']))
                grandtotal["klantID"]+=row['totaal']
            except ValueError:
                return apology("Wrong input", 406)
            except TypeError:
                rows = db.execute("SELECT * FROM ticketsoorten WHERE tekoop = 'true'")
                return render_template("kopen.html", name=klantID, tickets=rows)


        row['aantal']=str(int(row['aantal']))
        grandtotal["klantID"]=math.ceil(grandtotal["klantID"]*100)/100

        if grandtotal == 0:
            return apology('U heeft geen tickets besteld.',403)

        global bestelling
        bestelling=rows

        # Redirect admin to the admin page
        return render_template("bevestig.html" , name=klantID, tickets=rows, grandtotal=grandtotal["klantID"])

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        rows = db.execute("SELECT * FROM ticketsoorten WHERE tekoop = 'true'")
        return render_template("kopen.html", name=klantID, tickets=rows)


@app.route("/disclaimer", methods=["GET", "POST"] )
def disclaimer():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        print ("if - disclaimer")

        answer1=request.form.get("answer1")
        answer2=request.form.get("answer2")


        if answer1=="Ja":
            return redirect("/registreer")
        elif answer2=="Nee":
            return redirect("/")
        else:
            return render_template("disclaimer.html")


    else:
        return render_template("disclaimer.html")

@app.route("/registreer", methods=["GET", "POST"] )
def registreer():

    global klantID, klantnaam, klantnaam_volledig

    if request.method == "POST":

        errormsg=""

        try:
            voornaam = request.form.get("voornaam")
            tussenvoegsel = request.form.get("tussenvoegsel")
            achternaam = request.form.get("achternaam")
            emailadres = request.form.get("emailadres")
            telefoonnummer = request.form.get("telefoonnummer")
            username = request.form.get("username")
            password = request.form.get("password")

            klantnaam = voornaam
            klantnaam_volledig = voornaam
            if tussenvoegsel:
                klantnaam_volledig += " " + tussenvoegsel
            klantnaam_volledig += " " + achternaam

        except ValueError:
                return apology("Wrong input", 406)

        print("## "+username+" &&")

        if username=="":
            username = "no username"
            password = str(randint(1111, 9999))

        rows = db.execute("SELECT username FROM bezoeker ")
        for row in rows:
            if (row['username'] == username and username !="no username"):
                return apology("Sorry, deze username is al in gebruik.", 406)

        # Store client in the client database
        result = db.execute("INSERT INTO bezoeker (voornaam, tussenvoegsel, achternaam, emailadres, telefoonnummer, username, password) VALUES(:voornaam, :tussenvoegsel, :achternaam, :emailadres, :telefoonnummer, :username, :password)",
            voornaam=voornaam, tussenvoegsel=tussenvoegsel, achternaam=achternaam, emailadres=emailadres, telefoonnummer=telefoonnummer,
            username=username, password=password)

        if not result:
            return apology("Username allready exists!", 406)

        # store their id in session to log them in automatically
        user_id = db.execute("SELECT bz_id FROM bezoeker WHERE password IS :password AND emailadres IS :emailadres", password=password, emailadres=emailadres)
        session['user_id'] = user_id[0]['bz_id']
        klantID = session['user_id']

        cookie = cookies.SimpleCookie()
        cookie["klant"] = session["user_id"]

        return redirect("/kln_betalen")

    else:

        return render_template("registreer.html")

@app.route("/scantest")
def scantest():

    ticketnr = request.args.get('ticketnr')
    print(str(ticketnr))

    return render_template("gescand.html", ticketnr=ticketnr )


@app.route("/molliewebhook", methods=["GET", "POST"] )
def mollieWebhook():

    return apology("Webhook pinged", 406)

