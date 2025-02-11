# Advanced Scale Usage

You have learned how to create interactions and how to keep your code clean with scales.
The following examples show you how to elevate your scales to the next level.

## Check This Out

It would be cool the check some condition before invoking a command, wouldn't it?
You are in luck, that is exactly what checks are for.

Checks prohibit the interaction from running if they return `False`.

You can add your own check to your scale. In this example, we only want a user whose name starts with "a" to run any command from this scale.
```python
class MyScale(Scale):
    def __init__(self, client: Snake):
        self.client = client
        self.add_scale_check(self.a_check)

    async def a_check(ctx: InteractionContext) -> bool:
        return bool(ctx.author.name.startswith("a"))

    @slash_command(...)
    async def my_command(...):
        ...

def setup(client):
    MyScale(client)
```

## Pre- And Post-Run Events

Pre- and Post-Run events are similar to checks. They run before and after an interaction is invoked, respectively.

In this example, we are just printing some stats before and after the interaction.
```python
class MyScale(Scale):
    def __init__(self, client: Snake):
        self.client = client
        self.add_scale_prerun(self.pre_run)
        self.add_scale_postrun(self.post_run)

    async def pre_run(ctx: InteractionContext):
        print(f"Command started at: {datetime.datetime.now()}")

    async def post_run(ctx: InteractionContext):
        print(f"Command done at: {datetime.datetime.now()}")

    @slash_command(...)
    async def my_command(...):
        ...

def setup(client):
    MyScale(client)
```

## Global Checks

Now you learned how to make checks for a scale right after we told you to use scales to split your code into different files.
Ironic, if you want a check for any interaction in any scale.

Lucky you, however, since you seem to have forgotten about python subclassing.
By subclassing your own custom scale, your can still split your code into as many files as you want without having to redefine your checks.

### File 1
```python
class CustomScale(Scale):
    def __init__(self, client: Snake):
        self.client = client
        self.add_scale_check(self.a_check)

    async def a_check(ctx: InteractionContext) -> bool:
        return bool(ctx.author.name.startswith("a"))
```

### File 2
```python
class MyScale(CustomScale):
    @slash_command(...)
    async def my_command(...):
        ...

def setup(client):
    MyScale(client)
```
