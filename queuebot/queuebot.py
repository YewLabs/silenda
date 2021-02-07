#!/usr/bin/python3

import discord

from google.cloud import datastore

GLOBAL_DC = None

def getDatastoreClient():
    global GLOBAL_DC
    if not GLOBAL_DC:
        GLOBAL_DC = datastore.Client()
    return GLOBAL_DC

CACHED_MAPPING = {}

def getOrMakeMapping(name):
    dc = getDatastoreClient()
    k = dc.key('Mapping', name)
    mapping = dc.get(k)
    if not mapping:
        mapping = datastore.Entity(k)
        dc.put(mapping)
    return (dc, mapping)

def getMapping(name):
    if name in CACHED_MAPPING:
        return CACHED_MAPPING[name]
    _, s = getOrMakeMapping(name)
    if 'value' not in s:
        s['value'] = None
    CACHED_MAPPING[name] = s['value']
    return s['value']

def setMapping(name, value):
    dc, s = getOrMakeMapping(name)
    s['value'] = value
    CACHED_MAPPING[name] = s['value']
    dc.put(s)

client = discord.Client()

BACKEND = <BACKEND_CHANNEL>
FRONTEND = <FRONTEND_CHANNEL>

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.channel.id != BACKEND:
        return

    fchnl = client.get_channel(FRONTEND)
    if message.content.strip() == 'PURGE_ADMIN':
        count = 0
        async for m in fchnl.history(limit=None):
            if m.author == client.user:
                await m.delete()
                count += 1
        await message.channel.send('Purged %d' % (count))
    cid = getMapping(message.author.name)
    handled = True
    msg = None
    if cid:
        try:
            msg = await fchnl.fetch_message(cid)
        except:
            pass

    if message.content.strip() == 'DELETE':
        if msg:
            await msg.delete()
        setMapping(message.author.name, '')
    else:
        embed = None
        if message.embeds:
            embed = message.embeds[0]
        if msg:
            await msg.edit(content=message.content, embed=embed)
        else:
            msg = await fchnl.send(content=message.content, embed=embed)
            setMapping(message.author.name, msg.id)

client.run(<DISCORD_BOT_ID>)
