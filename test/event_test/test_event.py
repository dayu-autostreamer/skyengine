

from sky_executor.utils.event import EventTest,EventAgvFail

if __name__ == '__main__':
    # event=BaseEvent()
    # event_test=EventTest(status='trigger',payload={'DATA':233})
    # event_test_recover=EventTest(status='recover',payload={'DATA':233})
    # event()
    # event_test()
    # event_test_recover()
    # print(EventTest.event_type)
    from sky_executor.packet_factory.packet_factory.packet_factory_env.packet_factory_env import PacketFactoryEnv
    print(type(PacketFactoryEnv))


