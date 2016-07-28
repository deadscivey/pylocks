import time

from pylocks.testing.redis_test import RedisTest
from pylocks.testing.errors import BadNewsBears
from pylocks.core.lock_handle_data import LockHandleData
from pylocks.core.lock_request import LockRequest
from pylocks.errors import LockNotOwned, LockExpired, LockAlreadyHeld
from .single_lock_handle import SingleLockHandle
from .base_redis_lock import BaseRedisLock

def make_handle_data(key, handle_id, ttl=20):
    now = time.time()
    request_time = now - (ttl / 2)
    acquire_time = request_time + 1.5
    data = LockHandleData(
        request=LockRequest(
            key=key,
            initial_ttl=ttl,
            request_time=request_time,
            lock_arity=1,
            lock_prefix='foo',
            root_prefix='testlocks'
        ),
        id=handle_id,
        acquired_at=acquire_time
    )
    return data


class TestSingleLockHandle(RedisTest):
    def setUp(self):
        super(TestSingleLockHandle, self).setUp()
        self.lock = BaseRedisLock(redis_conn=self.r)

    def make_handle(self, key, handle_id):
        data = make_handle_data(key, handle_id)
        return SingleLockHandle(handle_data=data, redis_conn=self.r)

    def test_check_if_owned_1(self):
        handle = self.make_handle('some-lock', 'some-handle-id')
        with self.assertRaises(LockNotOwned):
            handle.check_if_owned()

    def test_check_if_owned_2(self):
        handle = self.make_handle('some-lock', 'some-handle-id')
        self.lock._debug_hard_set_handle(handle)
        handle.check_if_owned()

    def test_get_handle_1(self):
        with self.assertRaises(LockExpired):
            self.lock.get_handle('foo', 'bar')

    def test_releasing_1(self):
        handle_data = make_handle_data('foo', 'bar')
        handle = self.lock.acquire(handle_data.request)
        handle.check_if_owned()
        with self.assertRaises(BadNewsBears):
            with handle.releasing():
                raise BadNewsBears()

        with self.assertRaises(LockNotOwned):
            handle.check_if_owned()

    def test_releasing_2(self):
        acquire = lambda: self.lock.acquire(make_handle_data('foo', 'x').request)
        handle = acquire()
        handle.check_if_owned()

        with self.assertRaises(LockAlreadyHeld):
            acquire()

        with self.assertRaises(BadNewsBears):
            with handle.releasing():
                raise BadNewsBears()

        with self.assertRaises(LockNotOwned):
            handle.check_if_owned()

        handle2 = acquire()
        handle2.check_if_owned()

    def test_releasing_mismatched_id(self):
        handle = self.lock.acquire(make_handle_data('foo', 'x').request)
        handle.check_if_owned()
        handle.handle_data.id = 'bad!'
        with self.assertRaises(LockNotOwned):
            with self.assertRaises(BadNewsBears):
                with handle.releasing():
                    raise BadNewsBears

    def test_releasing_mismatched_id_no_failure(self):
        handle = self.lock.acquire(make_handle_data('foo', 'x').request)
        handle.check_if_owned()
        handle.handle_data.id = 'bad!'
        with self.assertRaises(BadNewsBears):
            with handle.releasing(ignore_failure=True):
                raise BadNewsBears
