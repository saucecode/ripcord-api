# ripcord-api

This is old, unnecessary, and probably out of date. Do not use it, except perhaps as a reference for your own work.

An unofficial list of discord API libraries can be found [here](https://discordapi.com/unofficial/libs.html). The majority of these libraries can be used to create Discord self-bots<sup>1</sup> (or can be easily modified to do so<sup>2</sup>), and eliminates the need for this library.

Below is the original README.md.

[1] *self-bot* meaning a programmable Discord bot masquerading as a real Discord user.  
[2] I did it with JDA.

-----

This project endeavors to reverse engineer as much of the unreleased Discord Client API as possible, and produce a library of functions that lets programmers:

 - Write a better, more fully featured, and open source Discord client.
 - Write bots which can respond to voice commands.
 - Implement optional E2EE in a Discord Client.

Also because message deletion is stupid.

[Proof of concept](https://www.youtube.com/watch?v=bQk-ZJPecSc) - Part of this project was ported to Java to write a small standalone client, just to show that it was possible.

## Currently implemented/figured out functions

These are functions of `DiscordClient`.

`login(email, password)`  
Sends a login request with email:password, and gets an authtoken.

`logout()`  
Sends a logout request. Closes websocket connection.

`get_me()`  
Gets information about the logged in user, saving the following information: username, email, phone number, avatar, id, discriminator, verified email.

`retrieve_websocket_gateway()`  
Gets the websocket URL. Usually `wss://gateway.discordapp.com/`.

`download_messages(channelid, limit=50)`  
Returns up to 50 (unless specified otherwise) messages from the channel `channelid`.

`connect_websocket(gateway_url)`  
Connects to and uses the websocket at `gateway_url`.

`send_message(channelid, message, tts=False, nonce="123")`  
Sends message with content `message` to the channel given by `channelid`. Optional flag to use Discord's TTS feature.

`send_start_typing(channelid)`  
Sends a signal to show that the user is typing in the channel given by `channelid`.

`send_presence_change(presence)`  
Changes the status of the user. `presence` can be one of `idle`, `online`, `dnd`, `invisible`.

`send_view_server(serverid)`  
Sends a (OP 12) signal declaring which server you are looking at. You will start receiving TYPING_START packets from users in these servers.

`retrieve_servers()`  
Retrieves a list of all the servers the current user is a member of.

`retrieve_server_channels(serverid)`  
Retrieves a list of channels in the server given by `serverid`. This will return ALL channels that exist, including voice channels, and channels that you are not a member of.

`retrieve_server_members(serverid)`  
Retrieves a list of members in the server given by `serverid`. Members who have a special nickname in `serverid` will have a 'nick' field.


The working project name is `Communication Security is Mandatory`.
