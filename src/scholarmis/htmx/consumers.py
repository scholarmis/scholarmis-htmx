from scholarmis.framework.asynco.websokets import WebsocketConsumer
from scholarmis.framework.asynco.channels import build_channel_group_name


class HTMXConsumer(WebsocketConsumer):
    
    rooms = []
    
    async def connect(self):
        self.tenant_schema = self.scope.get('tenant_schema')
        self.user = self.scope.get('user')
        
        # 1. Security Check
        if not self.tenant_schema or not self.user.is_authenticated:
            await self.close()
            return

        # 2. Define our targets
        self.rooms = [
            build_channel_group_name(self.tenant_schema, "system"),
            build_channel_group_name(self.tenant_schema, "user", [self.user.id]),
        ]

        # 3. Add Group/Role based room if it exists
        if hasattr(self.user, 'role') and self.user.role:
            self.rooms.append(
                build_channel_group_name(self.tenant_schema, "group", [self.user.role])
            )

        # 4. Join all rooms
        for room in self.rooms:
            await self.channel_layer.group_add(room, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        for room in self.rooms:
            await self.channel_layer.group_discard(room, self.channel_name)

    async def broadcast_message(self, event): 
        await self.send_data(event)
        
    async def user_message(self, event): 
        await self.send_data(event)
        
    async def group_message(self, event): 
        await self.send_data(event)


class TaskProgressConsumer(WebsocketConsumer):

    async def connect(self):
        self.tenant_schema = self.scope.get('tenant_schema')
        self.user = self.scope.get('user')
        self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
        self.group_name = build_channel_group_name(self.tenant_schema, "tasks", [self.user.id, self.task_id])

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )

    async def task_progress(self, event):
        await self.send_data(event)
