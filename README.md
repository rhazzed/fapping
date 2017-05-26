This is a respository for working with the piAware (flightaware for the Raspberry Pi) distribution.  It is a collection of quick PoC tools, scripts and code that a group of piAware users found useful. All code is provisional - we are testing out what is possible.  So feel free to investigate what we've done, and offer fixes, suggestions, (etc.).  We are a group of ADS-B monitoring fans. All suggestions (especially to up the gooder-ness) are welcome!

- The fap team

(P.S. "fap" came from the first tool we wrote - "FlightAware Profiler". Don't project your issues onto it... ;)

###################################################################
EMAIL CHAIN DESCRIBING THE TOOLS AND THEIR USE FOLLOWS
###################################################################
###################################################################

> Yet another tool - ason.  Don't bug me about the name... just let me
> have my fun!
> 
> I think this script (ason) will replace rawsb.  ason shows you
> the same information as rawsb, except instead of the "EMERGENCY" column
> it shows RSSI, which is the signal strength of each plane's messages.
> Plus, ason uses much less CPU (and much less network bandwidth), even
> though rawsb didn't use much CPU to begin with.
> 
> You have to add one entry to the lighttpd daemon's config file in order
> to get the data we need from the Pi, remotely.
> 
> In the file - /etc/lighttpd/conf-available/50-piaware.conf - you will
> need to add these lines -
> ============================================================
> 
> # Allow access to aircraft.json -
> alias.url += (
>     "/aircraft.json" => "/run/dump1090-fa/aircraft.json"
> )
> 
> 
> 
> 
> 
> 
> 
> 
> 
> 
> BEFORE ADDING THE ENTRY YOUR FILE MIGHT LOOK SOMETHING LIKE THIS -
> ==================================================================
> 
> # Allows access to the piaware status file, and
> # does translation rewrites for the landing page
> 
> alias.url += (
>     "/status.json" => "/run/piaware/status.json"
> )
> 
> server.modules += ( "mod_rewrite" )
> 
> $HTTP["language"] =~ "(en)" {
>     url.rewrite = ( "^/translations/lang.js$" => "/translations/%1.js" )
> }
> else $HTTP["language"] =~ ".*" {
>     url.rewrite = ( "^/translations/lang.js$" => "/translations/en.js" )
> }
> 
> 
> 
> 
> 
> 
> AFTER ADDING THE ENTRY YOUR FILE SHOULD LOOK SOMETHING LIKE THIS -
> ==================================================================
> 
> # Allows access to the piaware status file, and
> # does translation rewrites for the landing page
> 
> alias.url += (
>     "/status.json" => "/run/piaware/status.json"
> )
> 
> # Allow access to aircraft.json -
> alias.url += (
>     "/aircraft.json" => "/run/dump1090-fa/aircraft.json"
> )
> 
> server.modules += ( "mod_rewrite" )
> 
> $HTTP["language"] =~ "(en)" {
>     url.rewrite = ( "^/translations/lang.js$" => "/translations/%1.js" )
> }
> else $HTTP["language"] =~ ".*" {
>     url.rewrite = ( "^/translations/lang.js$" => "/translations/en.js" )
> }
> 
> 
> This should be picked up automatically.  If not, restart the lighttpd
> daemon (or reboot your pi), and "ason" should be able to remotely grab
> all the data it needs!
> 
> Enjoy!
> 
> 
> 
> On Wed, 2017-05-24 at 20:03 -0700, ka9cql wrote:
> > Fastats is a shell script that you run on the Raspberry Pi while it is
> > running the flightaware software (dump-1090 in particular). It helps
> > you see the noise level, 10 of the weakest and 10 of the strongest
> > signal levels as well as the average decoded message rate
> > (msgs/second). It runs once per command line invocation.
> > 
> > 
> > rawsb is an experimental text-only data display program. It need a
> > very wide and very tall text screen. It lists fata on around 70 planes
> > at once. It runs either on the pi (using a /usr/bin/ksh shell) or on a
> > network-connected Linux box (using /bin/sh), and takes one argument -
> > the IP address of the Pi (127.0.0.1 works).
> > 
> > 
> > fap.py is a neat real-time plot of signal strengths received, with
> > your receiver in the middle of the screen. Up is North, left is West,
> > etc.  It is a top-down view that either runs once (no arguments),
> > continuously (-c argument) or uses all of the data collected over the
> > past hour or so (-a).  The -a is colored by strength of signal, with 9
> > being the best/strongest.
> > 
> > 
> > fap.py and fap.py -c use a letter (A-I) and number (1-9) to indicate
> > each plane's height (A is very high and I is almost landing) and
> > received signal strength (0 is -33dbm, and every number higher is an
> > oncrease by 3db to a max of 9). Where the height is super super high
> > (possibly false?) I put a plus sign ('+') instead of a letter.
> > 
> > 
> > Each grid location in fap.py is about an 18x18 or 20x20 mile grid,
> > depending. The tool shows you what it is using presently.
> > 
> > 
> > I think fap.py is the most useful tool in general. fastats is
> > generally only needed upon initial setup, or if you want to play
> > around with the receiver gain setting of your SDR dongle. I like to
> > run it whenever I want to change antennas, or move one around, swap
> > cables, etc. And rawsb is just for information junkies. It will
> > probably morph into a full-on gui/console app.... eventually.
> > 
> > 
> > Let me know what you think. We can compare fap.py -a outputs directly.
> > It is independent of receiver, antenna etc. It truly is a bird's eye
> > view of your total system performance.
> > 
> > 
> > Let me know what you think!
> > 
> > 
> > 
> > 
> > -------- Original message --------
> > From: Mike 
> > Date: 5/24/17 5:44 PM (GMT-08:00) 
> > Subject: Re: Cool Flight Aware Antenna/Gain Tuning Tools 
> > 
> > I have attached the latest fap.py (fap.py).  Changes include a
> > little cleaner formatting for the header and footer. I also expanded
> > the
> > grid when using the "-a" (all reports) option to 500x500 miles.
> > 
> > I also added the latest tool I created called "rawsb" (rawsb).
> > That
> > script needs a tweak if it's to be run directly on the Pi, or from a
> > remote Linux box.  If running on a Pi, the first line in the script
> > should look like this -
> > 
> > #!/usr/bin/ksh
> > 
> > 
> > If running on a non-Pi Linux box it should look like this -
> > 
> > #!/bin/sh
> > 
> > 
> > It is *ABSOLUTELY* *CRITICAL* that the pound-sign and exclamation
> > point
> > be preserved.  There should be no spaces or tabs before the pound sign,
> > and it should be the very first line in the file.  Nothing above it.
> > 
> > (That is just a Linux thing.... nothing to do with the tool, per se...)
> > 
> > The rawsb tool takes one argument, the Pi's IP address.  If you are
> > running on the Pi, you can provide 127.0.0.1, the loopback address.
> > 
> > rawsb needs a WIDE and TALL text display screen.  I maximize the screen
> > in both dimensions, and run a smaller font.  It shows the text data from
> > up to 68 planes (I think) on one screen - so it needs all the space it
> > can get!  I find it interesting, if a bit overwhelming.  You guys may be
> > bored by it.... Either way, let me know what you think!
> > 
> > I haven't changed the fastats tools since I last sent you both a copy,
> > but I included it here anyway (fastats).
> > 
> > Enjoy, and let me know if you have any suggestions for improvements!
> > 
> > On Fri, 2017-05-05 at 12:00 -0700, Mike wrote:
> > > 
> > > My buddy and I changed some things on
> > > the ADS-B tools I sent you earlier.  The Python tool now has "pretty
> > > colors"!  It's much more visually appealing!  There is also more
> > > information about the grid being used, etc.
> > > 
> > > The shell script tool explains a little better what its list of signal
> > > strengths means, too.
> > > 
> > > 
> > > Testing has proven out the advice of adjusting your dongle's gain value
> > > until the "noise" reading that "fastats" displays is between -20db and
> > > -25db, with approximately -24db being a "sweet spot" for long-range
> > > signal reception.
> > > 
> > > The dongle's "auto gain" setting seems to have an advantage in the
> > > messages-per-second category (aka more position reports from the same
> > > aircraft), but does not see as many different planes, nor see them out
> > > as far as if you manually tune your gain according to the noise range I mentioned.
> > > 
> > > All-in-all, these are experimental tools, and so take them with a grain
> > > of salt.  But if you are a "tinkerer", then you will probably enjoy them.
> > > 
> > > 
> > > AS BEFORE: You can launch the "fastats" tool to generate a one-time
> > > report, or combine it with the "watch" tool (every Linux distro has "watch") like this -
> > >     watch fastats
> > >     - in order to re-run the tool once every 2 seconds.
> > > 
> > > The "fap.py" tool (which you just run by typing its name - don't need to
> > > put "python" before its name) has some changes.
> > > 
> > > Like before, running "fap.py" produces a one-time grid of contacts from
> > > the last 15 seconds or so.  The "A-J" letter indicates how high the
> > > plane is (a "+" means above 45,000 feet), and the 0-9 number indicates
> > > how strong the signal is.  A 0 means the signal was at or below -33db.
> > > Every number above that adds 3 db -- so a 1 means -30db, a 2 = -27, and
> > > so on.  Anything above -6db is displayed as a 9.
> > > 
> > > Changes to "fap.py" include the arguments "-c" (continuous) and
> > > "-a" (use all historical signal reports), and the "-a" now presents in
> > > beautiful "feng shue" (my friend's term) colors to help differentiate
> > > the signal strengths.  This output looks really compelling on a black
> > > background, if you have the choice.
> > > 
> > > Please let me know how you like these tools, and if you have any ideas
> > > on how to make them more useful or understandable, please let me know.
> > > My buddy and I will be releasing this code (such as it is!) pretty soon
> > > as open-source for the ADS-B monitoring community.  Suggestions welcome!
> > > 
> > > - Mike
> > > 
> > > 
> > > > -----Original Message-----
> > > > From: Mike
> > > > Sent: Tuesday, May 2, 2017 7:59 PM
> > > > Subject: Cool Flight Aware Antenna/Gain Tuning Tools
> > > > 
> > > > 
> > > > If you are so inclined, I have attached two tools that have proven invaluable 
> > > > in helping me and my friend tune our ADS-B receiver setup.
> > > > 
> > > > Both tools are run from the command line.  So either use a 
> > > > keyboard/mouse/monitor hooked up locally (bad option for remote-mounted 
> > > > sites!), or ssh into the box and run it from there.
> > > > 
> > > > One tool is a simple shell script, and the other is written in Python, which 
> > > > should already be installed on your Raspberry Pi.
> > > > 
> > > > The first tool - fastats - is a tool that will pull out data from the 
> > > > receiver, and display things like signal strength, noise level (THE most 
> > > > important!), a few more values, as well as the dynamic range of your receiver. 
> > > > It displays this by showing you the 10 weakest signals' strength (in db), 
> > > > followed by the 10 strongest signals' strength (also in db).
> > > > 
> > > > You could use this tool to adjust the gain setting of your dump1090 program, 
> > > > until the reported noise level lies somewhere between -23 and
> > > > -20 db.  This should give you adequate gain without oversaturating your 
> > > > receiver's front end.
> > > > 
> > > > After you adjust the gain to that level, you can see how wide a dynamic range 
> > > > your receiver has, given that gain level.  You should shoot for an 
> > > > installation where the weakest signals are between 20 and
> > > > 30 db down from the strongest.  (30 is an almost impossible goal, just
> > > > sayin...)
> > > > 
> > > > 
> > > > The second tool is a Python tool called "fap.py".  It stands for "Flight Aware 
> > > > Performance".  (lol)
> > > > 
> > > > fap.py repeatedly reads the last ten seconds' worth of collected aircraft 
> > > > data, and plots it on a x/y grid.  Your station is located right smack dab in 
> > > > the middle of the grid, and all signals received within the previous 10 
> > > > seconds are plotted according to where the plane was (relative to your shack) 
> > > > when it transmitted the beacon.
> > > > 
> > > > fap.py shows two values - a letter (A-J) that indicates the altitude of the 
> > > > plane (A = 35,000-40,000 ft, J = under 1,000 feet) - with one exception. 
> > > > Planes flying higher than 40,000 feet are denoted by a plus-sign ("+").
> > > > 
> > > > A second value displayed on the screen is a numeric signal-strength indicator. 
> > > > Think of it as an "S-meter", where a "9" is like an "S9" signal, and a 2 is
> > > > "S2", or barely readable.
> > > > 
> > > > For any one position on the grid, only the strongest received signal will be 
> > > > plotted.  Thus, if a plane flying at 3,000 feet, with a received signal 
> > > > strength of 4 is in roughly the same 8-mile by 8-mile grid (relative to your 
> > > > station) as a plane flying at 40,000 feet with a received signal strength of 
> > > > 7, the grid will only display the latter, stronger signal as an "A7".
> > > > 
> > > > If no signal was received from a given grid location within the previous 10 
> > > > seconds, I display two dots ".." at that location.
> > > > 
> > > > 
> > > > 
> > > > If you type "fap.py" and press <Enter>, the tool only reads the last
> > > > 10 seconds of the dump1090 program's history.
> > > > 
> > > > If you add the argument "-a" (or "all"), fap.py will look back, historically, 
> > > > over approximately the last 60 minutes, and generate the same plot - but this 
> > > > time using every single signal report, over this entire duration.
> > > > 
> > > > 
> > > > fap.py has one more option - "-c", or "continuous".  It does exactly what 
> > > > you'd expect - it runs continuously, refreshing the screen every four seconds 
> > > > or so.  To break out of this loop, press <Ctrl>-C.
> > > > 
> > > > 
> > > > 
> > > > If your "fap.py -a" plot shows more or less the same value in every signal 
> > > > location, then you have a problem.  Either your gain is too high, or your 
> > > > receiver (antenna) is not hearing very well.  Either way, I would start with 
> > > > the fastats tool, and tune your noise level to the -23 -to- -20 db level that 
> > > > I mentioned earlier.
> > > > 
> > > > 
> > > > 
> > > > 
> > > > If you find these tools useful, or can even get them to run on your box, I 
> > > > would love to see a screenshot / picture of the results.  I have only two test 
> > > > points so far, and I'd be interested in how they work for you.
> > > > 
> > > > Enjoy!
> > > > 
> > > > - Mike
> > > > 
> > > > 
